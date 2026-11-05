from src.research_agent import run_research


def main():
    print("IBM Granite Research Agent")

    topic = input("Enter your research topic: ").strip()

    if not topic:
        print("Please enter a valid topic.")
        return

    try:
        report, sources, report_path = run_research(topic)

        print("\nRESEARCH REPORT\n")
        print(report)

        print("\nSOURCES CONSULTED")
        for source in sources:
            print(source)

        print(f"\nReport saved at: {report_path}")

    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()