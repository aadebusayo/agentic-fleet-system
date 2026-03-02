package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/example/agent-platform/agent-fleet/internal/supervisor"
)

type monitorEvent struct {
	Module  string                 `json:"module"`
	Type    string                 `json:"type"`
	Message string                 `json:"message"`
	TraceID string                 `json:"traceId,omitempty"`
	AgentID string                 `json:"agentId,omitempty"`
	Health  string                 `json:"health,omitempty"`
	Payload map[string]interface{} `json:"payload,omitempty"`
}

func emitMonitorEvent(baseURL string, event monitorEvent) {
	body, err := json.Marshal(event)
	if err != nil {
		return
	}

	client := &http.Client{Timeout: 1500 * time.Millisecond}
	_, _ = client.Post(baseURL+"/monitor/events", "application/json", bytes.NewBuffer(body))
}

func main() {
	s := supervisor.NewSupervisor()
	controlPlaneBaseURL := os.Getenv("CONTROL_PLANE_BASE_URL")
	if controlPlaneBaseURL == "" {
		controlPlaneBaseURL = "http://localhost:8081"
	}

	http.HandleFunc("/register", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		var a supervisor.Agent
		if err := json.NewDecoder(r.Body).Decode(&a); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		s.Register(a)
		emitMonitorEvent(controlPlaneBaseURL, monitorEvent{
			Module:  "agent-fleet",
			Type:    "agent-spawned",
			Message: "Agent registered in fleet",
			AgentID: a.ID,
			Health:  "healthy",
			Payload: map[string]interface{}{"type": a.Type},
		})
		w.WriteHeader(http.StatusCreated)
	})

	log.Println("agent-fleet listening on :8082")
	if err := http.ListenAndServe(":8082", nil); err != nil {
		log.Fatal(err)
	}
}
