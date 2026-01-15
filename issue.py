from core.authority import issue_authority

authority = issue_authority()

print(
    f"AUTHORITY ISSUED "
    f"(v1, JTI={authority['jti']})"
)
