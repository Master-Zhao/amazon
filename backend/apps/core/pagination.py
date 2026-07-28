from dataclasses import dataclass

from rest_framework.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class PageSpec:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_spec(request, *, default_page_size: int = 50, max_page_size: int = 100) -> PageSpec:
    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", default_page_size))
    except (TypeError, ValueError) as exc:
        raise ValidationError({"pagination": "page/pageSize 必须为整数"}) from exc
    if page < 1 or page_size < 1 or page_size > max_page_size:
        raise ValidationError(
            {"pagination": f"page 必须大于 0，pageSize 必须为 1—{max_page_size}"}
        )
    return PageSpec(page=page, page_size=page_size)


def paginate_queryset(queryset, spec: PageSpec):
    total = queryset.count()
    items = list(queryset[spec.offset : spec.offset + spec.page_size])
    return items, pagination_payload(spec, total)


def paginate_sequence(items, spec: PageSpec):
    total = len(items)
    page_items = items[spec.offset : spec.offset + spec.page_size]
    return page_items, pagination_payload(spec, total)


def pagination_payload(spec: PageSpec, total: int) -> dict[str, int]:
    return {
        "page": spec.page,
        "page_size": spec.page_size,
        "total": total,
        "total_pages": (total + spec.page_size - 1) // spec.page_size,
    }
