from datetime import date


class SegmentPrefixBuilder:
    """Builds the physical line prefix."""

    def __init__(
        self,
        prefix_length: int = 25,
        prefix_length_field: str = "0000000",
        file_code: str = "NB2",
        constant_100: str = "100",
        constant_2: str = "2",
        suffix: str = "SE",
    ):
        self.prefix_length = prefix_length
        self.prefix_length_field = prefix_length_field
        self.file_code = file_code
        self.constant_100 = constant_100
        self.constant_2 = constant_2
        self.suffix = suffix

    def build_prefix(
        self,
        global_line_number: int,
        segment_number: int,
        generation_date: date,
    ) -> str:
        if global_line_number < 1:
            raise ValueError("global_line_number must be greater than zero")

        if segment_number < 1:
            raise ValueError("segment_number must be greater than zero")

        day_of_year = generation_date.timetuple().tm_yday

        prefix = (
            self.file_code
            + f"{day_of_year:03d}"
            + self.constant_100
            + self.prefix_length_field
            + self.constant_2
            + f"{global_line_number:05d}"
            + str(segment_number)
            + self.suffix
        )

        if len(prefix) != self.prefix_length:
            raise ValueError(
                f"Invalid prefix length: {len(prefix)}, "
                f"expected {self.prefix_length}. "
                f"Generated prefix = {prefix!r}"
            )

        return prefix
