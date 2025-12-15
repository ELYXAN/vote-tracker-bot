"""
Terminal Farben für schöne Ausgaben
Verwendet ANSI Escape Codes für Terminal-Farben
"""
import sys

# Prüfe ob Terminal Farben unterstützt
SUPPORTS_COLOR = sys.stdout.isatty() and hasattr(sys.stdout, 'isatty')


class Colors:
    """ANSI Farb-Codes für Terminal-Ausgaben"""
    
    # Reset
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Erfolg - Hellgrün (nicht zu grell)
    SUCCESS = '\033[92m'  # Bright Green
    SUCCESS_BOLD = '\033[1;92m'  # Bold Bright Green
    
    # Fehler - Hellrot (nicht zu grell)
    ERROR = '\033[91m'  # Bright Red
    ERROR_BOLD = '\033[1;91m'  # Bold Bright Red
    
    # Warnung - Gelb/Orange
    WARNING = '\033[93m'  # Bright Yellow
    WARNING_BOLD = '\033[1;93m'  # Bold Bright Yellow
    
    # Info - Cyan (für allgemeine Informationen)
    INFO = '\033[96m'  # Bright Cyan
    INFO_BOLD = '\033[1;96m'  # Bold Bright Cyan
    
    # Highlight - Magenta (für wichtige Hervorhebungen)
    HIGHLIGHT = '\033[95m'  # Bright Magenta
    HIGHLIGHT_BOLD = '\033[1;95m'  # Bold Bright Magenta
    
    # Prompt - Blau (für Eingabeaufforderungen)
    PROMPT = '\033[94m'  # Bright Blue
    PROMPT_BOLD = '\033[1;94m'  # Bold Bright Blue
    
    # Neutral - Weiß/Grau (für normale Texte)
    NEUTRAL = '\033[97m'  # Bright White
    DIM_TEXT = '\033[90m'  # Bright Black (grau)


def colorize(text, color_code):
    """Färbt Text ein, falls Terminal Farben unterstützt"""
    if not SUPPORTS_COLOR:
        return text
    return f"{color_code}{text}{Colors.RESET}"


def success(text, bold=False):
    """Grüner Text für Erfolgsmeldungen"""
    color = Colors.SUCCESS_BOLD if bold else Colors.SUCCESS
    return colorize(text, color)


def error(text, bold=False):
    """Roter Text für Fehlermeldungen"""
    color = Colors.ERROR_BOLD if bold else Colors.ERROR
    return colorize(text, color)


def warning(text, bold=False):
    """Gelber Text für Warnungen"""
    color = Colors.WARNING_BOLD if bold else Colors.WARNING
    return colorize(text, color)


def info(text, bold=False):
    """Cyan Text für Informationen"""
    color = Colors.INFO_BOLD if bold else Colors.INFO
    return colorize(text, color)


def highlight(text, bold=False):
    """Magenta Text für Hervorhebungen"""
    color = Colors.HIGHLIGHT_BOLD if bold else Colors.HIGHLIGHT
    return colorize(text, color)


def prompt(text, bold=False):
    """Blauer Text für Eingabeaufforderungen"""
    color = Colors.PROMPT_BOLD if bold else Colors.PROMPT
    return colorize(text, color)


def neutral(text, bold=False):
    """Weißer Text für normale Ausgaben"""
    color = Colors.NEUTRAL if not bold else Colors.BOLD + Colors.NEUTRAL
    return colorize(text, color)


def dim(text):
    """Grauer Text für weniger wichtige Informationen"""
    return colorize(text, Colors.DIM_TEXT)

