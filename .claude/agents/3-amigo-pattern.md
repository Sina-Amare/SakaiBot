# The "3 Amigo Agents" Pattern

The 3 Amigo Agents pattern is a collaborative approach where PM, UX, and Development agents work in concert to deliver balanced solutions that consider business requirements, user experience, and technical feasibility.

## Pattern Overview

```
        3 Amigo Collaboration
              ┌─────┐
              │ PM  │ - Business Requirements
              │Agent│ - Success Criteria
              └──┬──┘
                 │
          ┌──────┴──────┐
          │             │
      ┌───▼───┐    ┌────▼────┐
      │  UX   │    │   Dev   │
      │ Agent │◄──►│ Agents  │
      └───────┘    └─────────┘
      User Needs   Technical
      & Design     Feasibility
```

## Core Agents in the Pattern

### 1. PM Agent (Product/Project Management)
- **Role:** Define business requirements and success criteria
- **Focus:** What needs to be built and why
- **Outputs:** User stories, acceptance criteria, priorities

### 2. UX Specialist
- **Role:** Design user experience and interface
- **Focus:** How users will interact with the solution
- **Outputs:** Wireframes, prototypes, interaction patterns

### 3. Development Agents (Frontend/Backend/Database)
- **Role:** Technical implementation and feasibility
- **Focus:** How to build the solution efficiently
- **Outputs:** Technical specifications, code implementation

## Collaboration Workflow

### Phase 1: Discovery & Alignment
```
PM Agent → Gather requirements and define scope
    ↓
All 3 Agents → Collaborative refinement session
    ↓
Aligned understanding of goals, constraints, and approach
```

### Phase 2: Design & Planning
```
Parallel Work:
├── PM Agent: Detailed user stories and acceptance criteria
├── UX Agent: Wireframes and user flows
└── Dev Agents: Technical architecture and feasibility analysis

Convergence:
All 3 → Review and align on approach
```

### Phase 3: Implementation
```
Iterative Cycles:
1. UX Agent → Design specifications
2. Dev Agents → Implementation based on UX specs
3. PM Agent → Validation against requirements
4. All 3 → Review and iterate
```

## Usage Examples

### Example 1: New Feature Development
```
Task: "Add user authentication to the application"

3 Amigo Process:
1. PM Agent defines:
   - Business need for user accounts
   - Security requirements
   - Success metrics

2. UX Specialist designs:
   - Login/signup flows
   - Password recovery process
   - User dashboard

3. Dev Agents implement:
   - Authentication backend
   - Frontend components
   - Database schema
```

### Example 2: Performance Optimization
```
Task: "Improve page load time for mobile users"

3 Amigo Process:
1. PM Agent identifies:
   - Business impact of slow load times
   - Target performance metrics
   - User segments affected

2. UX Specialist proposes:
   - Progressive loading patterns
   - Skeleton screens
   - Optimized user journey

3. Dev Agents implement:
   - Code splitting
   - Image optimization
   - Caching strategies
```

## Benefits of the 3 Amigo Pattern

### 1. Balanced Solutions
- Business requirements are met
- User experience is optimized
- Technical constraints are considered

### 2. Early Problem Detection
- Feasibility issues identified before implementation
- UX problems caught before development
- Requirement gaps discovered early

### 3. Reduced Rework
- Fewer surprises during implementation
- Less back-and-forth between teams
- Clearer specifications from the start

### 4. Shared Understanding
- All perspectives considered upfront
- Common language and goals
- Aligned expectations

## Implementation Guidelines

### For Simple Tasks
```bash
# Invoke individually for quick tasks
/agents pm-agent "Define requirements for user profile page"
/agents ux-specialist "Design user profile wireframe"
/agents frontend-specialist "Implement profile component"
```

### For Complex Features
```bash
# Use team-lead to coordinate 3 Amigo collaboration
/agents team-lead "Coordinate 3 Amigo agents for e-commerce checkout flow"
```

### Manual Orchestration
```
You: "I need to implement a new dashboard. Let's use the 3 Amigo pattern."

1. First, let's get requirements from PM
   → /agents pm-agent

2. Now let's design the UX
   → /agents ux-specialist

3. Finally, let's plan the implementation
   → /agents backend-specialist
   → /agents frontend-specialist
```

## Best Practices

### 1. Start Together
- Begin with all three perspectives in the room
- Align on goals before diving into details
- Establish success criteria upfront

### 2. Iterate Frequently
- Regular check-ins between agents
- Quick feedback loops
- Adjust approach based on discoveries

### 3. Document Decisions
- Record why decisions were made
- Capture trade-offs discussed
- Maintain alignment documentation

### 4. Respect Expertise
- PM owns business requirements
- UX owns user experience
- Dev owns technical implementation
- But all contribute to each area

## Anti-Patterns to Avoid

### 1. Sequential Waterfall
❌ PM → UX → Dev (no collaboration)
✅ PM + UX + Dev (collaborative from start)

### 2. Skipping Perspectives
❌ PM + Dev (no UX consideration)
❌ UX + Dev (no business context)
✅ All three perspectives included

### 3. Late Involvement
❌ Bringing in Dev only after design is "done"
❌ UX designing without PM requirements
✅ All involved from discovery phase

## Measuring Success

### Collaboration Metrics
- Time from concept to implementation
- Number of requirement changes mid-development
- Rework percentage
- Stakeholder satisfaction

### Outcome Metrics
- Feature adoption rate
- User satisfaction scores
- Technical debt created
- Business goals achieved

## Integration with Other Patterns

The 3 Amigo pattern works well with:
- **Sequential Processing:** For phase-based work
- **Parallel Processing:** Each amigo can work simultaneously
- **Hierarchical Processing:** Team-lead coordinates the amigos

## Conclusion

The 3 Amigo Agents pattern ensures balanced, well-thought-out solutions by bringing together business, user, and technical perspectives from the start. This collaborative approach reduces rework, improves quality, and delivers better outcomes for all stakeholders.