# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

def get_version() -> str:
    MAJOR = "1"
    MINOR = "0"
    PATCH = "0"
    return f"v{MAJOR}.{MINOR}.{PATCH}"

if __name__ == "__main__":
    print(get_version())
