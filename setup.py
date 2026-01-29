"""Setup configuration for SakaiBot."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="sakaibot",
    version="2.0.0",
    author="Sina Amare",
    author_email="your.email@example.com",
    description="Advanced Telegram Userbot with AI Capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/SakaiBot",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/SakaiBot/issues",
        "Documentation": "https://github.com/yourusername/SakaiBot/docs",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Chat",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "telethon>=1.34.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "openai>=1.0.0",
        "google-genai>=0.1.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "tabulate>=0.9.0",
        "aiofiles>=23.0.0",
        "pytz>=2023.3",
        "SpeechRecognition>=3.10.0",
        "pydub>=0.25.1",
        "azure-cognitiveservices-speech>=1.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "optional": [],
    },
    entry_points={
        "console_scripts": [
            "sakaibot=src.cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    zip_safe=False,
)