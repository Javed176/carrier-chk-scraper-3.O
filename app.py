        "Entity Type": "—",
        "Operating Status": "NOT FOUND",
        "Phone Number": "—",
        "Email Address": "—",
        "Location": "—",
        "_found": False,
    }
    # Step 1: SAFER snapshot
    data = fetch_safer_snapshot(mc_number)
    if data is None:
        return result
    entity_type = data.get("entity_type", "")
    result["MC Number"] = format_mc_number(mc_number, entity_type)
    result["Carrier Name"] = data.get("carrier_name", "—") or "—"
    result["Entity Type"] = entity_type or "—"
    result["Operating Status"] = data.get("status", "—") or "—"
    result["Phone Number"] = data.get("phone", "—") or "—"
    result["Location"] = data.get("location", "—") or "—"
    result["_found"] = True
    time.sleep(REQUEST_DELAY)
    # Step 2: SMS Carrier Registration email
    dot = data.get("usdot", "")
    if dot:
        email = fetch_carrier_email(dot)
        result["Email Address"] = email if email else "—"
        time.sleep(REQUEST_DELAY)
    return result
