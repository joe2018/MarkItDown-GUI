"""Theme constants: colors, seeds, and other visual tokens.

We use Material 3 (Flet's default) with a single brand seed. Adjust here
to re-skin the entire app.
"""


class AppTheme:
    # Material 3 color scheme seed — drives all derived colors.
    # Microsoft blue, friendly to the markitdown brand.
    PRIMARY_SEED = "#0078D4"

    # Spacing tokens (Material 3 rhythm)
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 16
    SPACE_LG = 24
    SPACE_XL = 32

    # Corner radius tokens
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 16
