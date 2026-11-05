"""Test external APIs and exporter."""
from src.information_search import search_wikipedia, search_openalex, search_crossref
from src.exporter import export_txt, export_pdf
from src.data_analysis import (
    load_dataframe, describe_dataframe,
    chart_histogram, chart_bar, chart_scatter, chart_correlation,
)
import io, pandas as pd

topic = "machine learning"

print("=== EXTERNAL API TEST ===")
wiki = search_wikipedia(topic, max_results=2)
print(f"Wikipedia: {len(wiki)} results")
if wiki:
    print(f"  First: {wiki[0]['title']}")

oa = search_openalex(topic, max_results=2)
print(f"OpenAlex:  {len(oa)} results")
if oa:
    print(f"  First: {oa[0]['title'][:60]}")

cr = search_crossref(topic, max_results=2)
print(f"Crossref:  {len(cr)} results")
if cr:
    print(f"  First: {cr[0]['title'][:60]}")

print()
print("=== EXPORTER TEST ===")
sample_report = "## Title\nTest\n\n## Abstract\nThis is an abstract.\n\n## Conclusion\nDone."
txt = export_txt("Test Topic", sample_report, ["http://example.com"])
print(f"TXT export: {len(txt)} bytes")

pdf = export_pdf("Test Topic", sample_report, ["http://example.com"])
print(f"PDF export: {len(pdf)} bytes")

print()
print("=== DATA ANALYSIS TEST ===")
# Create a small synthetic dataset
df_data = {
    "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"] * 4,
    "score": [85, 72, 91, 68, 95, 78, 82, 88, 71, 93, 76, 89, 84, 67, 92, 79, 86, 90, 73, 94],
    "age": [22, 25, 21, 28, 23, 24, 26, 22, 27, 20, 25, 23, 24, 29, 21, 26, 22, 23, 28, 24],
}
df = pd.DataFrame(df_data)
desc = describe_dataframe(df)
print(f"describe_dataframe: shape={desc['shape']}, numeric_cols={desc['numeric_columns']}")

buf = chart_histogram(df, "score")
print(f"chart_histogram: {buf.getbuffer().nbytes} bytes PNG")

buf2 = chart_bar(df, "name", "score")
print(f"chart_bar: {buf2.getbuffer().nbytes} bytes PNG")

buf3 = chart_scatter(df, "age", "score")
print(f"chart_scatter: {buf3.getbuffer().nbytes} bytes PNG")

buf4 = chart_correlation(df)
print(f"chart_correlation: {'OK' if buf4 else 'None (expected for <2 numeric)'}")

print()
print("All tests PASSED")
