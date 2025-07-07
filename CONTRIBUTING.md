# 📋 Contributing to Autonomous AI Blog System

Thank you for your interest in contributing to the Autonomous AI Blog System! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### 🐛 Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Clear description** of the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, dependencies)
- **Log files** or error messages
- **Screenshots** if applicable

**Bug Report Template:**
```markdown
**Bug Description:**
A clear and concise description of the bug.

**To Reproduce:**
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior:**
What you expected to happen.

**Environment:**
- OS: [e.g. Ubuntu 20.04]
- Python: [e.g. 3.9.7]
- Version: [e.g. 2.1.0]

**Additional Context:**
Add any other context about the problem here.
```

### 💡 Suggesting Enhancements

Enhancement suggestions are welcomed! Please include:

- **Clear title** and description
- **Use case** and motivation
- **Proposed solution** or implementation ideas
- **Alternative solutions** you've considered
- **Impact assessment** on existing functionality

### 🔧 Code Contributions

#### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Add** tests for new functionality
5. **Ensure** all tests pass
6. **Update** documentation if needed
7. **Commit** with clear messages
8. **Push** to your fork
9. **Create** a Pull Request

#### Branch Naming Convention

- `feature/description` - New features
- `bugfix/issue-number` - Bug fixes
- `hotfix/critical-issue` - Critical fixes
- `docs/section-name` - Documentation updates
- `refactor/component-name` - Code refactoring

#### Commit Message Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(generator): add support for custom AI models
fix(fetcher): resolve session cleanup memory leak
docs(api): update endpoint documentation
test(scheduler): add unit tests for cron scheduling
```

## 🧪 Development Setup

### Prerequisites

- Python 3.8+
- Git
- Ollama (for AI features)
- Redis (optional, for enhanced caching)

### Local Development

1. **Clone your fork:**
```bash
git clone https://github.com/yourusername/ai-blog-system.git
cd ai-blog-system
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install development dependencies:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Set up environment:**
```bash
cp .env.example .env.dev
# Edit .env.dev with development settings
```

5. **Initialize database:**
```bash
python -c "from src.database.models import db_manager; db_manager.init_database()"
```

6. **Run tests:**
```bash
python -m pytest tests/ -v
```

### Development Tools

#### Code Quality

We use several tools to maintain code quality:

- **Black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Type checking
- **pytest** - Testing

#### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
pip install pre-commit
pre-commit install
```

This will run the following checks on each commit:
- Code formatting with Black
- Import sorting with isort
- Linting with flake8
- Type checking with mypy
- Basic tests

#### Running Quality Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run all tests
python -m pytest tests/ -v --cov=src/
```

## 📝 Code Standards

### Python Style Guide

- Follow **PEP 8** for Python code style
- Use **type hints** for all functions and methods
- Write **comprehensive docstrings** following Google style
- Keep **line length** under 88 characters (Black default)
- Use **meaningful variable and function names**

### Documentation Standards

- **Docstrings** for all public classes, methods, and functions
- **Type annotations** for function parameters and return values
- **Inline comments** for complex logic
- **README updates** for new features
- **API documentation** for new endpoints

### Example Code Style

```python
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process and analyze blog content for quality and SEO.
    
    This class provides methods to analyze content quality, extract
    metadata, and generate SEO recommendations for blog posts.
    
    Attributes:
        min_word_count: Minimum word count for content validation.
        quality_threshold: Minimum quality score for acceptance.
    """
    
    def __init__(self, min_word_count: int = 300, quality_threshold: float = 0.7) -> None:
        """Initialize the content processor.
        
        Args:
            min_word_count: Minimum word count for content validation.
            quality_threshold: Minimum quality score for acceptance.
        """
        self.min_word_count = min_word_count
        self.quality_threshold = quality_threshold
        logger.info(f"ContentProcessor initialized with min_words={min_word_count}")
    
    def analyze_content(
        self, 
        content: str, 
        title: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze content quality and extract metrics.
        
        Performs comprehensive analysis including readability, SEO factors,
        and engagement metrics to determine content quality.
        
        Args:
            content: The blog post content to analyze.
            title: The blog post title.
            metadata: Optional metadata for enhanced analysis.
            
        Returns:
            A dictionary containing analysis results with keys:
                - quality_score: Overall quality score (0-100)
                - readability_score: Readability score
                - seo_score: SEO optimization score
                - recommendations: List of improvement suggestions
                
        Raises:
            ValueError: If content is empty or too short.
            
        Example:
            >>> processor = ContentProcessor()
            >>> result = processor.analyze_content("Sample content...", "Title")
            >>> print(result['quality_score'])
            85.2
        """
        if not content or len(content.split()) < self.min_word_count:
            raise ValueError(f"Content must have at least {self.min_word_count} words")
        
        # Analysis implementation here...
        return {
            "quality_score": 85.2,
            "readability_score": 78.5,
            "seo_score": 82.1,
            "recommendations": ["Add more headers", "Include internal links"]
        }
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_generator/
│   ├── test_aggregator/
│   └── test_publisher/
├── integration/            # Integration tests
├── fixtures/              # Test data
└── conftest.py            # Pytest configuration
```

### Writing Tests

- **One test file per module** (`test_module_name.py`)
- **Descriptive test names** (`test_should_generate_content_when_valid_input`)
- **Use fixtures** for common test data
- **Mock external dependencies** (APIs, file system, etc.)
- **Test both success and failure cases**

### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from src.generator.generate_post import AIGenerator
from src.generator.quality_scorer import QualityScore


class TestAIGenerator:
    """Test suite for AI content generator."""
    
    @pytest.fixture
    def ai_generator(self):
        """Create AI generator instance for testing."""
        config = Mock()
        config.model_name = "test-model"
        config.timeout = 300
        config.min_content_length = 500
        return AIGenerator(config)
    
    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return {
            "title": "Test Blog Post",
            "sources": ["Sample source content for testing..."],
            "urls": ["https://example.com/article1"]
        }
    
    @patch('src.generator.generate_post.subprocess')
    async def test_should_generate_content_when_valid_input(
        self, 
        mock_subprocess, 
        ai_generator, 
        sample_content
    ):
        """Test successful content generation with valid input."""
        # Arrange
        mock_process = Mock()
        mock_process.communicate.return_value = (b"Generated content", b"")
        mock_process.returncode = 0
        mock_subprocess.create_subprocess_exec.return_value = mock_process
        
        # Act
        result = await ai_generator.generate_content(
            sample_content["title"],
            sample_content["sources"],
            sample_content["urls"]
        )
        
        # Assert
        assert result.content == "Generated content"
        assert result.validation_passed is True
        assert result.word_count > 0
        mock_subprocess.create_subprocess_exec.assert_called_once()
    
    async def test_should_raise_exception_when_empty_sources(self, ai_generator):
        """Test exception handling with empty sources."""
        with pytest.raises(ValueError, match="Sources cannot be empty"):
            await ai_generator.generate_content("Test Title", [], [])
```

### Test Coverage

Maintain **minimum 80% test coverage** for all new code:

```bash
# Run tests with coverage
python -m pytest tests/ --cov=src/ --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 📚 Documentation Guidelines

### Code Documentation

- **Docstrings** for all public APIs using Google style
- **Type hints** for better IDE support and clarity
- **Inline comments** for complex algorithms
- **README updates** for new features

### API Documentation

When adding new API endpoints:

1. **Document parameters** and responses
2. **Provide examples** with curl commands
3. **Update OpenAPI specification** if applicable
4. **Add authentication requirements**

### User Documentation

- **Update README** for user-facing changes
- **Add configuration examples** for new settings
- **Create tutorials** for complex features
- **Update troubleshooting guides**

## 🚀 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality
- **PATCH** version for backward-compatible bug fixes

### Release Checklist

1. **Update version** in `setup.py` and `__init__.py`
2. **Update CHANGELOG.md** with new features and fixes
3. **Run full test suite** and ensure all tests pass
4. **Update documentation** for new features
5. **Create release PR** and get approval
6. **Tag release** with version number
7. **Update deployment** documentation if needed

## 🆘 Getting Help

### Community Resources

- **GitHub Issues** - For bugs and feature requests
- **GitHub Discussions** - For questions and general discussion
- **Documentation** - Comprehensive guides and API reference

### Maintainer Contact

For urgent issues or security concerns:
- **Email**: maintainer@example.com
- **Discord**: [Community Server](https://discord.gg/example)

## 🏆 Recognition

Contributors will be recognized in:
- **README.md** contributors section
- **CHANGELOG.md** for significant contributions
- **Release notes** for major features

## 📜 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive environment for all contributors.

---

**Thank you for contributing to the Autonomous AI Blog System! 🎉**

Every contribution, no matter how small, helps make this project better for everyone.