Ensure that every development step adheres to GUIDELINES.md guidelines and verify that we are on the right track at each stage.

Environment: Python 3.10+ with async/await patterns
Language: Python
Task:
Generate a comprehensive project status report as a markdown file named `PROJECT_STATUS.md` in the project root directory. The report should include:

1. Current project state:

   - Recent changes or updates since the last analysis
   - Current version status and any pending releases
   - Active development branches or features in progress

2. File structure and code analysis:

   - Complete directory tree of the project
   - For each important file/module, provide:
     - Brief description of its purpose and functionality
     - Key classes/functions and their roles
     - Recent modifications or additions
     - Any TODO comments or unfinished features
     - Dependencies on other modules
   - Architecture patterns implemented and where they are used
   - Configuration files and their current settings

3. Technical status:

   - Current dependencies and any updates needed
   - Performance metrics and any identified bottlenecks
   - Recent error logs or issues encountered
   - Test coverage status and any failing tests

4. Development priorities:

   - Ranked list of planned features or improvements
   - Any technical debt that needs addressing
   - User feedback or feature requests received

5. Current challenges:

   - Technical obstacles or blockers
   - Areas where development is stuck or progressing slowly
   - Any architectural decisions that need to be made

6. Development environment:
   - Current setup for local development and testing
   - CI/CD pipeline status
   - Documentation that needs updating

Requirements:

- Use proper markdown formatting with headers, bullet points, and code blocks
- Include specific file paths and code examples where relevant
- Add any error messages or logs in code blocks for better readability
- Create a table of contents at the beginning for easy navigation
- For the file structure section, use tree format or nested lists
- Include code snippets for important functions or classes
- Add a "Next Steps" section with actionable items

Validation:
Verify that:

- The PROJECT_STATUS.md file is created in the project root
- All sections are properly formatted and complete
- All critical project components have been assessed
- The information is current and accurate
- The file is readable and well-structured
- The file structure section includes all important files and their descriptions.
