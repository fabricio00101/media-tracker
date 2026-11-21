import math

DEFAULT_PER_PAGE = 16
MAX_PER_PAGE = 50

# Tamaño mínimo por defecto (GB). Es la única fuente de verdad: la plantilla
# recibe este valor para el input visible y el campo oculto.
DEFAULT_MIN_SIZE_GB = 5

MIN_QUERY_LENGTH = 1
MAX_QUERY_LENGTH = 150
MIN_SIZE_GB_MIN = 0.0
MIN_SIZE_GB_MAX = 2000.0
MAX_QUALITY_TAG_LENGTH = 30
ALLOWED_CATEGORIES = {"all", "movies", "tv", "docs"}
ALLOWED_LANG_FILTERS = {"all", "latino", "castellano", "sub", "otros"}
ALLOWED_SORTS = {"seeders_desc", "bpp_desc", "year_desc", "year_asc", "title_asc"}
MIN_BPP_MIN = 0.0
MIN_BPP_MAX = 1.0


class ValidationError(Exception):
    """Error de validación de entrada HTTP."""

    def __init__(self, message, code="INVALID_PARAMETER", status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def parse_positive_int(value, default, minimum=1, maximum=None):
    """Convierte un parámetro de query string a entero acotado."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def validate_search_params(args):
    """Valida y normaliza todos los parámetros de búsqueda.

    Devuelve un diccionario limpio con los parámetros validados o lanza ValidationError.
    """
    # 1) Query
    raw_query = args.get("query", "").strip()
    if not raw_query:
        raise ValidationError(
            "El nombre de la búsqueda es requerido.",
            code="MISSING_QUERY",
            status=400,
        )
    if len(raw_query) > MAX_QUERY_LENGTH:
        raise ValidationError(
            f"La búsqueda no puede superar los {MAX_QUERY_LENGTH} caracteres.",
            code="QUERY_TOO_LONG",
            status=400,
        )

    # 2) Categoría
    category = args.get("category", "all").strip().lower()
    if category not in ALLOWED_CATEGORIES:
        raise ValidationError(
            f"Categoría inválida '{category}'. Valores permitidos: {', '.join(sorted(ALLOWED_CATEGORIES))}.",
            code="INVALID_CATEGORY",
            status=400,
        )

    # 3) Filtros de idioma
    lang_filter_raw = args.get("lang_filter", "all").strip().lower()
    lang_filters = [x.strip() for x in lang_filter_raw.split(",") if x.strip()]
    if not lang_filters:
        lang_filters = ["all"]
    invalid_langs = [l for l in lang_filters if l not in ALLOWED_LANG_FILTERS]
    if invalid_langs:
        raise ValidationError(
            f"Filtro de idioma inválido: {', '.join(invalid_langs)}. Valores permitidos: {', '.join(sorted(ALLOWED_LANG_FILTERS))}.",
            code="INVALID_LANG_FILTER",
            status=400,
        )

    # 4) Tamaño mínimo
    raw_min_size = args.get("min_size_gb", DEFAULT_MIN_SIZE_GB)
    try:
        min_size_gb = float(raw_min_size)
        if (
            not math.isfinite(min_size_gb)
            or min_size_gb < MIN_SIZE_GB_MIN
            or min_size_gb > MIN_SIZE_GB_MAX
        ):
            raise ValidationError(
                f"El tamaño mínimo debe ser un número finito entre {MIN_SIZE_GB_MIN} y {MIN_SIZE_GB_MAX} GB.",
                code="INVALID_SIZE_RANGE",
                status=400,
            )
    except (ValueError, TypeError):
        raise ValidationError(
            "El parámetro min_size_gb debe ser un valor numérico válido.",
            code="INVALID_SIZE_FORMAT",
            status=400,
        )

    # 5) Calidad
    quality_tag = args.get("quality_tag", "").strip().lower()
    if len(quality_tag) > MAX_QUALITY_TAG_LENGTH:
        raise ValidationError(
            f"El filtro de calidad no puede superar los {MAX_QUALITY_TAG_LENGTH} caracteres.",
            code="QUALITY_TAG_TOO_LONG",
            status=400,
        )

    require_hdr = args.get("hdr", "false").lower() == "true"
    require_hevc = args.get("hevc", "false").lower() == "true"
    sdr_only = args.get("sdr_only", "false").lower() == "true"

    # 6) Calidad mínima estimada (bits por píxel) y criterio de orden
    raw_min_bpp = args.get("min_bpp", 0)
    try:
        min_bpp = float(raw_min_bpp)
        if (
            not math.isfinite(min_bpp)
            or min_bpp < MIN_BPP_MIN
            or min_bpp > MIN_BPP_MAX
        ):
            raise ValidationError(
                f"La calidad mínima (min_bpp) debe estar entre {MIN_BPP_MIN} y {MIN_BPP_MAX}.",
                code="INVALID_BPP_RANGE",
                status=400,
            )
    except (ValueError, TypeError):
        raise ValidationError(
            "El parámetro min_bpp debe ser un valor numérico válido.",
            code="INVALID_BPP_FORMAT",
            status=400,
        )

    sort = args.get("sort", "seeders_desc").strip().lower()
    if sort not in ALLOWED_SORTS:
        raise ValidationError(
            f"Criterio de orden inválido '{sort}'. Valores permitidos: {', '.join(sorted(ALLOWED_SORTS))}.",
            code="INVALID_SORT",
            status=400,
        )

    page = parse_positive_int(args.get("page", 1), 1)
    per_page = parse_positive_int(
        args.get("per_page", DEFAULT_PER_PAGE),
        DEFAULT_PER_PAGE,
        maximum=MAX_PER_PAGE,
    )

    return {
        "query": raw_query,
        "category": category,
        "lang_filters": lang_filters,
        "min_size_gb": min_size_gb,
        "quality_tag": quality_tag,
        "require_hdr": require_hdr,
        "require_hevc": require_hevc,
        "sdr_only": sdr_only,
        "min_bpp": min_bpp,
        "sort": sort,
        "page": page,
        "per_page": per_page,
    }
