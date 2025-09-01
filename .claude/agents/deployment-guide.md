# Multi-Agent Architecture Deployment Guide

This guide explains how to deploy the multi-agent architecture to your other projects and customize it for different technology stacks.

## Quick Start: Deploy to Any Project

### Option 1: Copy Full Agent Library (Recommended)
```bash
# From your current project directory, copy all agents to target project
cp -r .claude/agents /path/to/your/other/project/.claude/
```

### Option 2: Selective Agent Deployment
```bash
# Copy only core agents for minimal setup
mkdir -p /path/to/target/project/.claude/agents
cp .claude/agents/code-reviewer.md /path/to/target/project/.claude/agents/
cp .claude/agents/debugger.md /path/to/target/project/.claude/agents/
cp .claude/agents/tester.md /path/to/target/project/.claude/agents/
cp .claude/agents/refactor-specialist.md /path/to/target/project/.claude/agents/
```

## Project-Specific claude.md Configuration

### Do NOT modify your existing claude.md files
Your current project-specific claude.md files should remain unchanged. Instead, create a **new section** at the bottom of each project's claude.md file:

```markdown
# Multi-Agent Architecture

This project uses the Claude Code Multi-Agent Architecture for enhanced development productivity.

## Available Agents

### Core Development Team
- `code-reviewer` - Code quality and security analysis
- `debugger` - Issue investigation and resolution  
- `tester` - Test creation and validation
- `refactor-specialist` - Code optimization and cleanup

### Technology Specialists (customize based on your stack)
- `frontend-specialist` - UI/UX implementation
- `backend-specialist` - API and database work
- `devops-specialist` - CI/CD and infrastructure
- `security-auditor` - Vulnerability assessment

### Domain Experts
- `performance-optimizer` - Speed and efficiency improvements
- `documentation-writer` - Technical documentation
- `api-designer` - REST/GraphQL API architecture

### Orchestration
- `team-lead` - Multi-agent coordination for complex tasks
- `pm-agent` - Project management and requirements
- `architecture-agent` - System design and technical decisions

## Usage Patterns

### Simple Tasks
Invoke individual agents directly:
- `/agents code-reviewer` - Review current code changes
- `/agents debugger` - Investigate and fix bugs
- `/agents tester` - Create tests for new features

### Complex Tasks  
Use orchestration patterns via team-lead:
- `/agents team-lead` - Coordinate multi-agent workflows
- Sequential: Research → Design → Implement → Test
- Parallel: Frontend + Backend + Database simultaneously
- Hierarchical: Team leads coordinate specialist agents

## Project Customization
Customize agents for your specific tech stack by editing the agent files in `.claude/agents/`. 
Update technology references, coding standards, and tool preferences as needed.
```

## Technology-Specific Customizations

### Web Applications (React/Next.js + Node.js)
```bash
# Copy web-specific agents
cp .claude/agents/frontend-specialist.md /path/to/web/project/.claude/agents/
cp .claude/agents/backend-specialist.md /path/to/web/project/.claude/agents/

# Then edit the agents to specify:
# - React/Next.js in frontend-specialist.md  
# - Node.js/Express in backend-specialist.md
# - Add project-specific styling frameworks (Tailwind, etc.)
```

### Python/Django Projects
```bash
# Customize backend specialist for Python/Django
# Edit backend-specialist.md to reference:
# - Python best practices
# - Django ORM patterns
# - Python testing frameworks (pytest)
# - Python-specific security considerations
```

### Data Science/ML Projects
```bash
# Copy AI/ML specific agents (if you create them)
cp .claude/agents/data-analyst.md /path/to/ml/project/.claude/agents/
cp .claude/agents/ml-engineer.md /path/to/ml/project/.claude/agents/
cp .claude/agents/jupyter-specialist.md /path/to/ml/project/.claude/agents/
```

## Agent Customization Examples

### Customize Code Reviewer for Your Standards
Edit `.claude/agents/code-reviewer.md`:
```markdown
## Review Standards
- Follow [YOUR_COMPANY] coding standards
- Check for [YOUR_SECURITY_FRAMEWORK] compliance
- Validate [YOUR_ERROR_HANDLING] patterns
- Ensure [YOUR_LOGGING_FRAMEWORK] usage
```

### Customize Frontend Specialist for Your Stack
Edit `.claude/agents/frontend-specialist.md`:
```markdown
## Technology Expertise
- **Primary Framework** - React 18, Next.js 14
- **Styling** - Tailwind CSS, Styled Components
- **State Management** - Zustand, React Query
- **Testing** - Vitest, React Testing Library
```

## Per-Project Agent Management

### Minimal Setup (4 Core Agents)
For simple projects, use only:
- `code-reviewer.md`
- `debugger.md` 
- `tester.md`
- `refactor-specialist.md`

### Standard Setup (8 Agents)
For typical web applications, add:
- `frontend-specialist.md`
- `backend-specialist.md`
- `devops-specialist.md`
- `security-auditor.md`

### Full Setup (12+ Agents)
For complex enterprise projects, include all agents:
- All core and standard agents
- `performance-optimizer.md`
- `documentation-writer.md`
- `api-designer.md`
- `team-lead.md`
- `pm-agent.md`
- `architecture-agent.md`

## Maintenance Strategy

### Option 1: Independent Project Agents
- ✅ **Pro:** Complete customization per project
- ✅ **Pro:** No cross-project dependencies
- ❌ **Con:** Must update each project manually
- ❌ **Con:** Improvements don't propagate automatically

### Option 2: Symlinked Shared Library
```bash
# Create shared agent library
mkdir ~/.claude-agents
cp .claude/agents/* ~/.claude-agents/

# Symlink in each project
ln -s ~/.claude-agents /path/to/project/.claude/agents
```
- ✅ **Pro:** Central updates propagate everywhere
- ✅ **Pro:** Consistent behavior across projects
- ❌ **Con:** Less per-project customization
- ❌ **Con:** Risk of breaking changes affecting all projects

### Option 3: Git Submodule (Advanced)
```bash
# Add agent library as git submodule
git submodule add https://github.com/yourorg/claude-agents.git .claude/agents
```

## Best Practices for Multi-Project Deployment

### 1. Start Small
- Deploy core 4 agents first
- Test with existing codebase
- Gradually add specialized agents

### 2. Customize Gradually  
- Begin with generic agents
- Customize based on actual usage patterns
- Update agent prompts based on real feedback

### 3. Track Performance
- Use `baseline-metrics.md` framework in each project
- Compare performance improvements across projects
- Share successful patterns between projects

### 4. Team Training
- Train team on agent usage patterns
- Create project-specific usage documentation
- Establish agent usage standards

## FAQ

### Q: Do I need to change my existing claude.md files?
**A: No.** Keep your existing claude.md files unchanged. Just add the multi-agent section at the bottom.

### Q: Should I copy all agents to every project?
**A: Start with core agents, add others as needed.** Not every project needs every agent.

### Q: How do I update agents across multiple projects?
**A: Choose your maintenance strategy.** Independent copies for maximum customization, or symlinks/submodules for centralized updates.

### Q: Can I mix generic and project-specific agents?
**A: Yes.** Keep core agents generic and create project-specific variants for specialized needs.

### Q: What if my tech stack isn't covered?
**A: Customize existing agents.** Edit the technology references in existing agents to match your stack.

## Implementation Checklist

### Pre-Deployment
- [ ] Choose deployment strategy (copy vs symlink vs submodule)
- [ ] Identify which agents are needed for the project
- [ ] Plan customization requirements

### During Deployment  
- [ ] Create `.claude/agents/` directory
- [ ] Copy/link selected agents
- [ ] Update project claude.md with agent documentation
- [ ] Customize agents for project tech stack

### Post-Deployment
- [ ] Test agents with project codebase
- [ ] Train team on agent usage
- [ ] Establish baseline metrics
- [ ] Plan regular agent updates and maintenance

This deployment strategy allows you to scale the multi-agent architecture across all your projects while maintaining flexibility for project-specific needs.