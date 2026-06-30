"""EXIF tag name resolution and human-readable value decoding."""
from __future__ import annotations
from typing import Any, Optional


class TagDecoder:
    ORIENTATION = {1: "Normal (Top-Left)", 2: "Mirrored Horizontal", 3: "Rotated 180°",
                   4: "Mirrored Vertical", 5: "Mirrored Horizontal + Rotated 270° CW",
                   6: "Rotated 90° CW", 7: "Mirrored Horizontal + Rotated 90° CW", 8: "Rotated 270° CW"}
    EXPOSURE_PROGRAM = {0: "Not Defined", 1: "Manual", 2: "Normal Program", 3: "Aperture Priority",
                         4: "Shutter Priority", 5: "Creative Program", 6: "Action Program",
                         7: "Portrait Mode", 8: "Landscape Mode", 9: "Bulb"}
    METERING_MODE = {0: "Unknown", 1: "Average", 2: "Center-Weighted Average", 3: "Spot",
                      4: "Multi-Spot", 5: "Multi-Segment", 6: "Partial", 255: "Other"}
    FLASH = {0x00: "No Flash", 0x01: "Flash Fired", 0x05: "Flash Fired, Return Not Detected",
              0x07: "Flash Fired, Return Detected", 0x09: "Flash Fired, Compulsory On",
              0x0D: "Flash Fired, Compulsory On, Return Not Detected",
              0x0F: "Flash Fired, Compulsory On, Return Detected",
              0x10: "Flash Off, Compulsory Off", 0x18: "Flash Auto, Did Not Fire",
              0x19: "Flash Fired, Auto Mode", 0x1D: "Flash Fired, Auto, Return Not Detected",
              0x1F: "Flash Fired, Auto, Return Detected", 0x20: "No Flash Function",
              0x41: "Flash Fired, Red-Eye Reduction",
              0x45: "Flash Fired, Red-Eye Reduction, Return Not Detected",
              0x47: "Flash Fired, Red-Eye Reduction, Return Detected",
              0x49: "Flash Fired, Compulsory On, Red-Eye Reduction",
              0x4D: "Flash Fired, Compulsory On, Red-Eye Reduction, Return Not Detected",
              0x4F: "Flash Fired, Compulsory On, Red-Eye Reduction, Return Detected",
              0x59: "Flash Fired, Auto, Red-Eye Reduction",
              0x5D: "Flash Fired, Auto, Red-Eye Reduction, Return Not Detected",
              0x5F: "Flash Fired, Auto, Red-Eye Reduction, Return Detected"}
    COLOR_SPACE = {1: "sRGB", 2: "Adobe RGB", 65535: "Uncalibrated"}
    SENSING_METHOD = {1: "Not Defined", 2: "One-Chip Color Area Sensor", 3: "Two-Chip Color Area Sensor",
                       4: "Three-Chip Color Area Sensor", 5: "Color Sequential Area Sensor",
                       7: "Trilinear Sensor", 8: "Color Sequential Linear Sensor"}
    SCENE_CAPTURE_TYPE = {0: "Standard", 1: "Landscape", 2: "Portrait", 3: "Night Scene", 4: "Other"}
    EXPOSURE_MODE = {0: "Auto Exposure", 1: "Manual Exposure", 2: "Auto Bracket"}
    WHITE_BALANCE = {0: "Auto", 1: "Manual"}
    GAIN_CONTROL = {0: "None", 1: "Low Gain Up", 2: "High Gain Up", 3: "Low Gain Down", 4: "High Gain Down"}
    CONTRAST = {0: "Normal", 1: "Soft (Low)", 2: "Hard (High)"}
    SATURATION = {0: "Normal", 1: "Low", 2: "High"}
    SHARPNESS = {0: "Normal", 1: "Soft", 2: "Hard"}
    SUBJECT_DISTANCE_RANGE = {0: "Unknown", 1: "Macro", 2: "Close View", 3: "Distant View"}
    FILE_SOURCE = {1: "Film Scanner", 2: "Reflection Print Scanner", 3: "Digital Still Camera"}
    SCENE_TYPE = {1: "Directly Photographed"}
    CUSTOM_RENDERED = {0: "Normal Process", 1: "Custom Process", 2: "HDR (no original saved)",
                        3: "HDR (original saved)", 4: "Original (for HDR)", 6: "Panorama",
                        7: "Portrait HDR", 8: "Portrait"}
    LIGHT_SOURCE = {0: "Unknown", 1: "Daylight", 2: "Fluorescent", 3: "Tungsten (Incandescent)",
                     4: "Flash", 9: "Fine Weather", 10: "Cloudy Weather", 11: "Shade",
                     17: "Standard Light A", 18: "Standard Light B", 19: "Standard Light C",
                     20: "D55", 21: "D65", 22: "D75", 23: "D50", 24: "ISO Studio Tungsten", 255: "Other"}
    RESOLUTION_UNIT = {1: "No Absolute Unit", 2: "Inches (DPI)", 3: "Centimeters (DPCM)"}
    YCBCR_POSITIONING = {1: "Centered", 2: "Co-sited"}
    COMPRESSION = {1: "Uncompressed", 6: "JPEG (Old-Style)", 7: "JPEG", 8: "Adobe Deflate"}
    PHOTOMETRIC_INTERPRETATION = {0: "WhiteIsZero", 1: "BlackIsZero", 2: "RGB", 6: "YCbCr"}
    GPS_ALTITUDE_REF = {0: "Above Sea Level", 1: "Below Sea Level"}
    GPS_SPEED_REF = {"K": "km/h", "M": "mph", "N": "knots"}
    GPS_DIRECTION_REF = {"T": "True North", "M": "Magnetic North"}
    GPS_STATUS = {"A": "Measurement Active", "V": "Measurement Void"}
    GPS_MEASURE_MODE = {"2": "2-Dimensional", "3": "3-Dimensional"}
    GPS_DIFFERENTIAL = {0: "No Correction", 1: "Differential Corrected"}

    _ENUM_MAP = {
        "Orientation": ORIENTATION, "ExposureProgram": EXPOSURE_PROGRAM, "MeteringMode": METERING_MODE,
        "Flash": FLASH, "ColorSpace": COLOR_SPACE, "SensingMethod": SENSING_METHOD,
        "SceneCaptureType": SCENE_CAPTURE_TYPE, "ExposureMode": EXPOSURE_MODE, "WhiteBalance": WHITE_BALANCE,
        "GainControl": GAIN_CONTROL, "Contrast": CONTRAST, "Saturation": SATURATION, "Sharpness": SHARPNESS,
        "SubjectDistanceRange": SUBJECT_DISTANCE_RANGE, "FileSource": FILE_SOURCE, "SceneType": SCENE_TYPE,
        "CustomRendered": CUSTOM_RENDERED, "LightSource": LIGHT_SOURCE, "ResolutionUnit": RESOLUTION_UNIT,
        "YCbCrPositioning": YCBCR_POSITIONING, "Compression": COMPRESSION,
        "PhotometricInterpretation": PHOTOMETRIC_INTERPRETATION, "GPSAltitudeRef": GPS_ALTITUDE_REF,
        "GPSSpeedRef": GPS_SPEED_REF, "GPSImgDirectionRef": GPS_DIRECTION_REF,
        "GPSTrackRef": GPS_DIRECTION_REF, "GPSDestBearingRef": GPS_DIRECTION_REF,
        "GPSStatus": GPS_STATUS, "GPSMeasureMode": GPS_MEASURE_MODE, "GPSDifferential": GPS_DIFFERENTIAL,
    }

    # Tags whose raw value needs numeric formatting rather than enum lookup
    _FORMATTERS: dict = {}  # populated below after method definitions

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        try:
            if hasattr(value, "numerator") and hasattr(value, "denominator"):
                return float(value.numerator) / float(value.denominator) if value.denominator else None
            if isinstance(value, (tuple, list)) and len(value) == 2:
                return float(value[0]) / float(value[1]) if value[1] else None
            return float(value)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @classmethod
    def format_exposure_time(cls, value: Any) -> str:
        val = cls._to_float(value)
        if val is None or val <= 0:
            return str(value) if value is not None else ""
        if val >= 1:
            return f"{int(val)} sec" if val == int(val) else f"{val:.1f} sec"
        denom = round(1.0 / val)
        return f"1/{denom} sec"

    @classmethod
    def format_f_number(cls, value: Any) -> str:
        val = cls._to_float(value)
        if val is None:
            return str(value) if value is not None else ""
        return f"f/{val:.0f}" if val == int(val) else f"f/{val:.1f}"

    @classmethod
    def format_focal_length(cls, value: Any) -> str:
        val = cls._to_float(value)
        if val is None:
            return str(value) if value is not None else ""
        return f"{val:.0f} mm" if val == int(val) else f"{val:.1f} mm"

    @classmethod
    def format_iso(cls, value: Any) -> str:
        if isinstance(value, (tuple, list)):
            value = value[0] if value else None
        if value is None:
            return ""
        try:
            return f"ISO {int(value)}"
        except (TypeError, ValueError):
            return f"ISO {value}"

    @classmethod
    def format_exposure_bias(cls, value: Any) -> str:
        val = cls._to_float(value)
        if val is None:
            return str(value) if value is not None else ""
        if val == 0:
            return "0 EV"
        sign = "+" if val > 0 else ""
        return f"{sign}{val:.1f} EV"

    @classmethod
    def format_gps_coord(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    @classmethod
    def decode_components_config(cls, raw) -> str:
        m = {0: "-", 1: "Y", 2: "Cb", 3: "Cr", 4: "R", 5: "G", 6: "B"}
        if isinstance(raw, bytes):
            vals = list(raw)
        elif isinstance(raw, (tuple, list)):
            vals = list(raw)
        else:
            return str(raw)
        parts = [m.get(v, "?") for v in vals]
        res = ", ".join(parts)
        if res == "Y, Cb, Cr, -":
            return "YCbCr"
        if res == "R, G, B, -":
            return "RGB"
        return res

    @classmethod
    def decode(cls, tag_name: str, raw_value: Any) -> Any:
        """Return a human-readable decoded value for a given tag name."""
        if raw_value is None:
            return None
        formatter = cls._FORMATTERS.get(tag_name)
        if formatter:
            return formatter.__func__(cls, raw_value)
        table = cls._ENUM_MAP.get(tag_name)
        if table is not None:
            decoded = table.get(raw_value)
            if decoded is not None:
                return decoded
            if isinstance(raw_value, str):
                try:
                    return table.get(int(raw_value), raw_value)
                except (TypeError, ValueError):
                    pass
            return raw_value
        if tag_name == "ComponentsConfiguration":
            return cls.decode_components_config(raw_value)
        return raw_value

    @classmethod
    def get_tag_name(cls, tag_id: int, fallback_prefix: str = "Tag") -> str:
        try:
            from PIL.ExifTags import TAGS
            name = TAGS.get(tag_id)
            if name:
                return name
        except ImportError:
            pass
        return f"{fallback_prefix}_0x{tag_id:04X}"

    @classmethod
    def get_gps_tag_name(cls, tag_id: int) -> str:
        try:
            from PIL.ExifTags import GPSTAGS
            name = GPSTAGS.get(tag_id)
            if name:
                return name
        except ImportError:
            pass
        return f"GPSTag_0x{tag_id:04X}"


TagDecoder._FORMATTERS = {
    "ExposureTime": TagDecoder.format_exposure_time,
    "FNumber": TagDecoder.format_f_number,
    "ApertureValue": TagDecoder.format_f_number,
    "FocalLength": TagDecoder.format_focal_length,
    "FocalLengthIn35mmFilm": TagDecoder.format_focal_length,
    "ISOSpeedRatings": TagDecoder.format_iso,
    "PhotographicSensitivity": TagDecoder.format_iso,
    "ExposureBiasValue": TagDecoder.format_exposure_bias,
}
