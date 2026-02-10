from setuptools import setup, find_packages

setup(
    name="dart-pricing-pipeline",
    version="0.1.0",
    description="ComEd pricing data acquisition and analysis pipeline",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "streamlit>=1.33",
        "plotly>=5.20",
        "pandas>=2.2",
        "requests>=2.32",
        "plotly-express>=0.4",
    ],
    extras_require={
        "dev": [
            "pytest>=8.2",
        ]
    },
    python_requires=">=3.10",
)