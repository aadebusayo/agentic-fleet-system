package supervisor

import "testing"

func TestSpawnAgentRespectsDelegationLimit(t *testing.T) {
	s := NewSupervisor()
	parent := Agent{ID: "parent", MaxDelegations: 0, MaxRecursion: 2}
	s.Register(parent)

	err := s.SpawnAgent("parent", Agent{ID: "child", MaxDelegations: 1, MaxRecursion: 1}, 1)
	if err == nil {
		t.Fatalf("expected delegation limit error")
	}
}

func TestAssignCapability(t *testing.T) {
	s := NewSupervisor()
	s.Register(Agent{ID: "a1", MaxDelegations: 2, MaxRecursion: 2})
	if err := s.AssignCapability("a1", "route-task"); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
