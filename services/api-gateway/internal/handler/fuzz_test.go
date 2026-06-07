package handler

import (
	"encoding/json"
	"testing"
)

// FuzzControlMessageParsing tests that parsing arbitrary JSON into controlMessage never panics.
func FuzzControlMessageParsing(f *testing.F) {
	// Add some seed corpus
	f.Add([]byte(`{"action":"start","patient_id":"p1","practitioner_id":"pr1","encounter_id":"e1"}`))
	f.Add([]byte(`{"action":"stop"}`))
	f.Add([]byte(`{}`))
	f.Add([]byte(`invalid json`))
	f.Add([]byte(`{"action": 123}`)) // Invalid type
	
	f.Fuzz(func(t *testing.T, data []byte) {
		var ctrl controlMessage
		_ = json.Unmarshal(data, &ctrl)
		
		// The main goal is to ensure unmarshaling doesn't panic.
		// If it unmarshals successfully, we can do some sanity checks.
		if ctrl.Action != "" {
			// just validating it's a string, which Go type system handles,
			// but we can check if anything weird happens.
		}
	})
}
