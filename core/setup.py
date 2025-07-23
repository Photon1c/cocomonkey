from setuptools import setup, find_packages

setup(
    name="monkeyball",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        ".": ["*.json"],
        "data": ["*.json", "*.csv"],
        "profiles": ["*.json"],
    },
    install_requires=[
        "pygame>=2.6.1",
        "asyncio",
        "pandas",
        "python-dotenv",
        "numpy",
        "imageio",  # For GIF recording
    ],
    entry_points={
        "console_scripts": [
            "monkeyball=run_game:main",
        ],
    },
) 