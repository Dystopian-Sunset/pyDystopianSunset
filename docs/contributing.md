# Contributing Guide

Thank you for your interest in contributing to Quillian Undercity! This guide will help you get started.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone <your-fork-url>
   cd pyDystopianSunset
   ```
3. **Set up development environment**
   ```bash
   make install-dev
   make services-up
   make migrate
   make seed
   ```

## Contribution Areas

We welcome contributions in many areas:

### Code Contributions
- Bug fixes
- New features
- Performance improvements
- Code refactoring
- Test coverage

### Documentation
- Improving existing docs
- Adding examples
- Fixing typos
- Translating documentation

### Game Content
- New character classes
- Quest ideas and implementations
- NPC designs
- World-building content

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-description
```

Use descriptive branch names:
- `feature/add-inventory-system`
- `fix/character-deletion-bug`
- `docs/update-installation-guide`

### 2. Make Your Changes

- Follow the [coding standards](development.md#coding-standards)
- Write clear, descriptive commit messages
- Keep changes focused and atomic

### 3. Test Your Changes

```bash
# Run all checks
make check-all

# Run tests
make test

# Test the bot locally
make run-dev
```

### 4. Commit Your Changes

Use clear, descriptive commit messages:

```bash
git commit -m "Add feature: inventory management system"
git commit -m "Fix: character deletion foreign key error"
```

### 5. Push and Create Pull Request

```bash
git push origin feature/my-feature
```

Then create a pull request on GitHub.

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Format with `ruff`: `make format`
- Lint with `ruff`: `make lint`

### Code Organization

- One class per file (when possible)
- Group related functionality
- Use descriptive names
- Add docstrings to public functions/classes

### Database Changes

- Always create migrations for schema changes
- Test migrations on sample data
- Document complex migrations
- Never edit applied migrations

### Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for good test coverage
- Test edge cases

## Pull Request Process

### Before Submitting

- [ ] Code is formatted: `make format`
- [ ] Linting passes: `make lint`
- [ ] Type checking passes: `make typecheck`
- [ ] Tests pass: `make test`
- [ ] Documentation updated (if needed)
- [ ] Migration created (if models changed)

### PR Description

Include:
- What changes were made
- Why the changes were needed
- How to test the changes
- Screenshots (if UI changes)
- Related issues

### Review Process

- Maintainers will review your PR
- Address any feedback
- PRs are merged after approval and CI passes

## Code Review Guidelines

### For Contributors

- Be open to feedback
- Respond to comments promptly
- Make requested changes
- Ask questions if unclear

### For Reviewers

- Be constructive and respectful
- Explain reasoning for suggestions
- Approve when satisfied
- Request changes when needed

## Reporting Bugs

### Before Reporting

1. Check if the bug already exists in issues
2. Try to reproduce the bug
3. Check logs for error messages

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- Python version
- OS
- Bot version/commit

**Logs**
Relevant error messages or logs
```

## Feature Requests

### Before Requesting

1. Check if the feature already exists
2. Check if it's already planned
3. Consider if it fits the project vision

### Feature Request Template

```markdown
**Feature Description**
Clear description of the feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches you've thought about
```

## Game Content Contributions

### Character Classes

To add a new character class:

1. Add to seed data in `src/ds_common/seed_data.py`
2. Define associated stats
3. Add description and emoji
4. Run seed script: `make seed`

### Quests

Quest system is in development. Contributions welcome!

### NPCs

NPC generation is AI-powered. You can contribute by:
- Improving NPC generation prompts
- Adding NPC templates
- Enhancing NPC interaction logic

## Documentation Contributions

Documentation improvements are always welcome:

- Fix typos
- Clarify confusing sections
- Add examples
- Improve structure
- Add missing information

## Questions?

- Open an issue for discussion
- Check existing documentation
- Ask in Discord (if available)

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md (if created)
- Credited in release notes
- Appreciated by the community!

Thank you for contributing to Quillian Undercity! 🎮

