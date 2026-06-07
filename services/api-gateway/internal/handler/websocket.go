// Package handler provides HTTP and WebSocket handlers for the API Gateway.
package handler

import (
	"context"
	"encoding/json"
	"log/slog"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/kraionyx/shared/pkg/crypto"
	"github.com/kraionyx/shared/pkg/models"

	"github.com/kraionyx/api-gateway/internal/kafka"
	"github.com/kraionyx/api-gateway/internal/session"
)

const (
	// Time allowed to write a message to the peer.
	writeWait = 10 * time.Second

	// Time allowed to read the next pong message from the peer.
	pongWait = 60 * time.Second

	// Send pings to peer with this period. Must be less than pongWait.
	pingPeriod = (pongWait * 9) / 10

	// Maximum message size allowed from peer (1MB).
	maxMessageSize = 1024 * 1024
)

// controlMessage represents a JSON control message sent by the WebSocket client.
type controlMessage struct {
	Action         string `json:"action"`
	PatientID      string `json:"patient_id,omitempty"`
	PractitionerID string `json:"practitioner_id,omitempty"`
	EncounterID    string `json:"encounter_id,omitempty"`
}

// ackMessage represents a server acknowledgment sent back to the client.
type ackMessage struct {
	Status     string `json:"status"`
	ChunkIndex int    `json:"chunk_index,omitempty"`
	SessionID  string `json:"session_id,omitempty"`
	Message    string `json:"message,omitempty"`
}

// errorMessage represents a server error message sent to the client.
type errorMessage struct {
	Status  string `json:"status"`
	Message string `json:"message"`
}

// WebSocketHandler holds dependencies for the WebSocket audio stream handler.
type WebSocketHandler struct {
	sessionMgr    *session.Manager
	producer      *kafka.Producer
	encryptionKey []byte
	logger        *slog.Logger
}

type Client struct {
	conn             *websocket.Conn
	handler          *WebSocketHandler
	send             chan []byte
	currentSessionID string
	logger           *slog.Logger

	msgCount    int
	lastMsgTime time.Time
}

// NewWebSocketHandler creates a new WebSocket audio stream handler.
func NewWebSocketHandler(
	sessionMgr *session.Manager,
	producer *kafka.Producer,
	encryptionKey []byte,
	logger *slog.Logger,
) *WebSocketHandler {
	return &WebSocketHandler{
		sessionMgr:    sessionMgr,
		producer:      producer,
		encryptionKey: encryptionKey,
		logger:        logger.With(slog.String("component", "websocket_handler")),
	}
}

// Upgrade returns the Fiber middleware that upgrades HTTP connections to WebSocket.
func (h *WebSocketHandler) Upgrade() fiber.Handler {
	return func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	}
}

// HandleAudioStream handles incoming WebSocket audio connections.
//
// Protocol:
//  1. Client sends JSON control message: {"action": "start", "patient_id": "...", "practitioner_id": "...", "encounter_id": "..."}
//  2. Client streams binary audio frames (PCM 16kHz 16-bit mono, 500ms chunks)
//  3. Server acknowledges each chunk with JSON: {"status": "ok", "chunk_index": N}
//  4. Client sends JSON control message: {"action": "stop"} to end session
func (h *WebSocketHandler) HandleAudioStream() func(*websocket.Conn) {
	return func(c *websocket.Conn) {
		client := &Client{
			conn:        c,
			handler:     h,
			send:        make(chan []byte, 256),
			logger:      h.logger.With(slog.String("remote_addr", c.RemoteAddr().String())),
			lastMsgTime: time.Now(),
		}

		client.logger.Info("websocket connection established")

		// Allow collection of memory referenced by the caller by doing all work in
		// new goroutines.
		go client.writePump()
		client.readPump()
	}
}

// readPump pumps messages from the websocket connection.
// The application runs readPump in a per-connection goroutine.
func (c *Client) readPump() {
	defer func() {
		if c.currentSessionID != "" {
			// Best-effort close on disconnect.
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_, closeErr := c.handler.sessionMgr.CloseSession(ctx, c.currentSessionID)
			if closeErr != nil {
				c.logger.Warn("failed to close session on disconnect",
					slog.String("session_id", c.currentSessionID),
					slog.String("error", closeErr.Error()),
				)
			}
		}
		c.conn.Close()
		close(c.send)
		c.logger.Info("websocket connection closed")
	}()

	c.conn.SetReadLimit(maxMessageSize)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	for {
		msgType, msg, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				c.logger.Error("websocket read error", slog.String("error", err.Error()))
			} else {
				c.logger.Info("client closed websocket connection normally")
			}
			break
		}

		now := time.Now()
		if now.Sub(c.lastMsgTime) > time.Second {
			c.msgCount = 0
			c.lastMsgTime = now
		}
		c.msgCount++
		if c.msgCount > 100 {
			c.sendError("rate limit exceeded")
			continue
		}

		switch msgType {
		case websocket.TextMessage:
			c.handleTextMessage(msg)

		case websocket.BinaryMessage:
			if c.currentSessionID == "" {
				c.sendError("no active session, send start control message first")
				continue
			}
			c.handleBinaryMessage(msg)

		default:
			c.logger.Warn("unexpected websocket message type", slog.Int("type", msgType))
		}
	}
}

// writePump pumps messages from the hub to the websocket connection.
// A goroutine running writePump is started for each connection.
func (c *Client) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case msg, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				// The hub closed the channel.
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := c.conn.WriteMessage(websocket.TextMessage, msg); err != nil {
				c.logger.Error("failed to write websocket message", slog.String("error", err.Error()))
				return
			}
		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (c *Client) handleTextMessage(msg []byte) {
	var ctrl controlMessage
	if err := json.Unmarshal(msg, &ctrl); err != nil {
		c.sendError("invalid JSON control message")
		return
	}

	switch ctrl.Action {
	case "start":
		if c.currentSessionID != "" {
			c.sendError("session already active, send stop first")
			return
		}

		if ctrl.PatientID == "" || ctrl.PractitionerID == "" || ctrl.EncounterID == "" {
			c.sendError("patient_id, practitioner_id, and encounter_id are required")
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		sess, err := c.handler.sessionMgr.CreateSession(
			ctx,
			ctrl.PatientID,
			ctrl.PractitionerID,
			ctrl.EncounterID,
		)
		if err != nil {
			c.logger.Error("failed to create session", slog.String("error", err.Error()))
			c.sendError("failed to create session")
			return
		}

		c.currentSessionID = sess.ID
		c.logger.Info("session started", slog.String("session_id", sess.ID))

		ack := ackMessage{
			Status:    "ok",
			SessionID: sess.ID,
			Message:   "session started",
		}
		c.sendJSON(ack)

	case "stop":
		if c.currentSessionID == "" {
			c.sendError("no active session to stop")
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		sess, err := c.handler.sessionMgr.CloseSession(
			ctx,
			c.currentSessionID,
		)
		if err != nil {
			c.logger.Error("failed to close session",
				slog.String("session_id", c.currentSessionID),
				slog.String("error", err.Error()),
			)
			c.sendError("failed to close session")
			return
		}

		c.logger.Info("session stopped",
			slog.String("session_id", c.currentSessionID),
			slog.Int("total_chunks", sess.ChunkCount),
		)

		ack := ackMessage{
			Status:    "ok",
			SessionID: c.currentSessionID,
			Message:   "session stopped",
		}
		c.sendJSON(ack)
		c.currentSessionID = ""

	default:
		c.sendError("unknown action: " + ctrl.Action)
	}
}

func (c *Client) handleBinaryMessage(audioData []byte) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	chunkIndex, err := c.handler.sessionMgr.IncrementChunkCount(ctx, c.currentSessionID)
	if err != nil {
		c.logger.Error("failed to increment chunk count",
			slog.String("session_id", c.currentSessionID),
			slog.String("error", err.Error()),
		)
		c.sendError("session tracking error")
		return
	}

	// Chunk index is 0-based for the message, Redis returns 1-based count.
	msgChunkIndex := chunkIndex - 1

	encryptedData, err := crypto.Encrypt(audioData, c.handler.encryptionKey)
	if err != nil {
		c.logger.Error("failed to encrypt audio chunk",
			slog.String("session_id", c.currentSessionID),
			slog.String("error", err.Error()),
		)
		c.sendError("encryption error")
		return
	}

	msg := models.AudioChunkMessage{
		SessionID:   c.currentSessionID,
		ChunkIndex:  msgChunkIndex,
		TimestampMS: time.Now().UnixMilli(),
		AudioData:   encryptedData,
		Format:      "pcm_16khz",
		SampleRate:  16000,
		Channels:    1,
	}

	if err := c.handler.producer.PublishAudioChunk(context.Background(), msg); err != nil {
		c.logger.Error("failed to publish audio chunk",
			slog.String("session_id", c.currentSessionID),
			slog.Int("chunk_index", msgChunkIndex),
			slog.String("error", err.Error()),
		)
		c.sendError("publish error")
		return
	}

	c.logger.Debug("audio chunk processed",
		slog.String("session_id", c.currentSessionID),
		slog.Int("chunk_index", msgChunkIndex),
		slog.Int("audio_bytes", len(audioData)),
	)

	ack := ackMessage{
		Status:     "ok",
		ChunkIndex: msgChunkIndex,
	}
	c.sendJSON(ack)
}

func (c *Client) sendJSON(v interface{}) {
	b, err := json.Marshal(v)
	if err != nil {
		c.logger.Error("failed to marshal json", slog.String("error", err.Error()))
		return
	}
	select {
	case c.send <- b:
	default:
		c.logger.Warn("websocket send buffer full, dropping message")
	}
}

func (c *Client) sendError(message string) {
	c.sendJSON(errorMessage{Status: "error", Message: message})
}
