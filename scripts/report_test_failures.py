"""Expose bounded JUnit failure details in GitHub Actions annotations."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def report(path: Path) -> None:
    if not path.is_file():
        print("No JUnit report was produced; inspect the preceding failed step.")
        return
    count = 0
    for case in ET.parse(path).iter("testcase"):
        for result in case:
            if result.tag not in {"failure", "error"}:
                continue
            title = f"{case.get('classname', '')}.{case.get('name', '')}"
            title = escape(title).replace(":", "%3A").replace(",", "%2C")
            detail = result.text or result.get("message", "No failure details")
            print(f"::error title={title}::{escape(detail[:6000])}")
            count += 1
            if count == 20:
                print("Further failures are available in the JUnit artifact.")
                return


if __name__ == "__main__":
    report(Path(sys.argv[1] if len(sys.argv) > 1 else "test-results.xml"))
