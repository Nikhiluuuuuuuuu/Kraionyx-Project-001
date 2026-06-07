package main

import (
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

var (
	wsURL       = flag.String("url", "wss://localhost:8443/ws/audio", "WebSocket URL")
	concurrency = flag.Int("c", 100, "Number of concurrent connections")
	duration    = flag.Duration("d", 10*time.Second, "Duration of the test")
	
	successCount int64
	errorCount   int64
)

type controlMessage struct {
	Action         string `json:"action"`
	PatientID      string `json:"patient_id,omitempty"`
	PractitionerID string `json:"practitioner_id,omitempty"`
	EncounterID    string `json:"encounter_id,omitempty"`
}

func simulateClient(wg *sync.WaitGroup, id int) {
	defer wg.Done()

	dialer := *websocket.DefaultDialer
	dialer.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}

	conn, _, err := dialer.Dial(*wsURL, nil)
	if err != nil {
		atomic.AddInt64(&errorCount, 1)
		log.Printf("Client %d connect error: %v", id, err)
		return
	}
	defer conn.Close()

	// Send start control
	startMsg := controlMessage{
		Action:         "start",
		PatientID:      fmt.Sprintf("patient-load-%d", id),
		PractitionerID: fmt.Sprintf("practitioner-load-%d", id),
		EncounterID:    fmt.Sprintf("encounter-load-%d", id),
	}
	if err := conn.WriteJSON(startMsg); err != nil {
		atomic.AddInt64(&errorCount, 1)
		return
	}

	// Read ack
	_, msg, err := conn.ReadMessage()
	if err != nil {
		atomic.AddInt64(&errorCount, 1)
		return
	}
	
	var ack map[string]interface{}
	json.Unmarshal(msg, &ack)
	if status, ok := ack["status"].(string); !ok || status != "ok" {
		atomic.AddInt64(&errorCount, 1)
		return
	}

	endTime := time.Now().Add(*duration)
	for time.Now().Before(endTime) {
		// Send some dummy binary data
		dummyAudio := make([]byte, 1024)
		rand.Read(dummyAudio)
		if err := conn.WriteMessage(websocket.BinaryMessage, dummyAudio); err != nil {
			atomic.AddInt64(&errorCount, 1)
			return
		}

		// Read ack
		_, _, err = conn.ReadMessage()
		if err != nil {
			atomic.AddInt64(&errorCount, 1)
			return
		}

		atomic.AddInt64(&successCount, 1)
		time.Sleep(100 * time.Millisecond) // Simulating 100ms chunks
	}

	stopMsg := controlMessage{Action: "stop"}
	conn.WriteJSON(stopMsg)
}

func main() {
	flag.Parse()

	log.Printf("Starting load test with %d concurrent connections for %v", *concurrency, *duration)
	var wg sync.WaitGroup

	startTime := time.Now()

	for i := 0; i < *concurrency; i++ {
		wg.Add(1)
		go simulateClient(&wg, i)
		time.Sleep(10 * time.Millisecond) // ramp up
	}

	wg.Wait()
	
	elapsed := time.Since(startTime)
	log.Printf("Load test complete in %v.", elapsed)
	log.Printf("Successful chunks: %d", successCount)
	log.Printf("Errors: %d", errorCount)
	if successCount > 0 {
		log.Printf("Throughput: %.2f chunks/sec", float64(successCount)/elapsed.Seconds())
	}
}
