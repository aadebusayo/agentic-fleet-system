package supervisor

import (
	"errors"
	"sync"
)

type Agent struct {
	ID               string
	Type             string
	Capabilities     []string
	MaxRecursion     int
	MaxDelegations   int
	CurrentDelegates int
	Healthy          bool
}

type AgentFleetSupervisor struct {
	mu      sync.RWMutex
	agents  map[string]*Agent
	traceID string
}

func NewSupervisor() *AgentFleetSupervisor {
	return &AgentFleetSupervisor{
		agents: make(map[string]*Agent),
	}
}

func (s *AgentFleetSupervisor) Register(agent Agent) {
	s.mu.Lock()
	defer s.mu.Unlock()
	a := agent
	a.Healthy = true
	s.agents[agent.ID] = &a
}

func (s *AgentFleetSupervisor) SpawnAgent(parentID string, child Agent, depth int) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	parent, ok := s.agents[parentID]
	if !ok {
		return errors.New("parent agent not found")
	}
	if depth > parent.MaxRecursion {
		return errors.New("recursion limit exceeded")
	}
	if parent.CurrentDelegates >= parent.MaxDelegations {
		return errors.New("delegation limit exceeded")
	}

	parent.CurrentDelegates++
	c := child
	c.Healthy = true
	s.agents[child.ID] = &c
	return nil
}

func (s *AgentFleetSupervisor) AssignCapability(agentID string, capability string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	agent, ok := s.agents[agentID]
	if !ok {
		return errors.New("agent not found")
	}
	agent.Capabilities = append(agent.Capabilities, capability)
	return nil
}

func (s *AgentFleetSupervisor) MonitorHealth(agentID string) (bool, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	agent, ok := s.agents[agentID]
	if !ok {
		return false, errors.New("agent not found")
	}
	return agent.Healthy, nil
}
