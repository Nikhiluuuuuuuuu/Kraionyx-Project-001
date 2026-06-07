package fhir

type DocumentReference struct {
	ResourceType string `json:"resourceType"`
	ID           string `json:"id"`
	Status       string `json:"status"`
	DocStatus    string `json:"docStatus"`
}

type DiagnosticReport struct {
	ResourceType string `json:"resourceType"`
	ID           string `json:"id"`
	Status       string `json:"status"`
}
