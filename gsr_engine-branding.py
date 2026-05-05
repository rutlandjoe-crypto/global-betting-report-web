def build_report_header(client, report_date):
    product_name = client.get("product_name", "Report")
    return f"{product_name} | {report_date}"


def build_disclaimer(client):
    if not client.get("show_disclaimer", True):
        return ""
    return client.get(
        "disclaimer_text",
        "This report is an automated summary intended to support, not replace, human sports journalism."
    )


def section_enabled(client, section_name):
    return client.get("sections", {}).get(section_name, True)