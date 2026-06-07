package fhir

import (
	"regexp"
	"time"
)

type DocumentReferenceBuilder struct {
	doc *DocumentReference
}

func NewDocumentReferenceBuilder() *DocumentReferenceBuilder {
	return &DocumentReferenceBuilder{
		doc: &DocumentReference{
			ResourceType: "DocumentReference",
			Status:       "current",
			DocStatus:    "preliminary",
		},
	}
}

func (b *DocumentReferenceBuilder) WithPatient(id, display string) *DocumentReferenceBuilder {
	return b
}

func (b *DocumentReferenceBuilder) WithSOAPContent(soap string, encounterTime time.Time) *DocumentReferenceBuilder {
	// Strict PHI Redaction (e.g., SSN and generic phone number patterns)
	ssnRegex := regexp.MustCompile(`\b\d{3}-\d{2}-\d{4}\b`)
	phoneRegex := regexp.MustCompile(`\b\d{3}-\d{3}-\d{4}\b`)
	
	redacted := ssnRegex.ReplaceAllString(soap, "[REDACTED SSN]")
	redacted = phoneRegex.ReplaceAllString(redacted, "[REDACTED PHONE]")
	
	// Set the content somewhere (stub)
	// b.doc.Content = redacted
	return b
}

func (b *DocumentReferenceBuilder) Build() (*DocumentReference, error) {
	return b.doc, nil
}
