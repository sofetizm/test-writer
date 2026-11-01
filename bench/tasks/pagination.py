"""Pagination metadata for list endpoints."""


def paginate(total: int, page: int, per_page: int = 20, max_per_page: int = 100) -> dict:
    """Return metadata for `page` (1-based) of a list with `total` items.

    per_page is capped at max_per_page. A page beyond the last one is clamped to the
    last page; with total == 0 there is a single empty page 1.
    Result keys: page, pages, per_page, offset, has_prev, has_next.
    Raises ValueError if total < 0, page < 1 or per_page < 1.
    """
    if total < 0:
        raise ValueError("total must not be negative")
    if page < 1:
        raise ValueError("page must be at least 1")
    if per_page < 1:
        raise ValueError("per_page must be at least 1")
    per_page = min(per_page, max_per_page)
    pages = max(1, -(-total // per_page))
    page = min(page, pages)
    return {
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "offset": (page - 1) * per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
    }
