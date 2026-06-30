# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os

DEFAULT_HOURLY_RATE = float(os.environ.get("MILIMO_HOURLY_RATE", "100"))
FLOOR_MULTIPLIER = float(os.environ.get("MILIMO_FLOOR_MULTIPLIER", "0.8"))
CEILING_MULTIPLIER = float(os.environ.get("MILIMO_CEILING_MULTIPLIER", "1.5"))
TARGET_MARGIN_PERCENT = float(os.environ.get("MILIMO_TARGET_MARGIN", "30"))
PLATFORM_FEE_PERCENT = float(os.environ.get("MILIMO_PLATFORM_FEE_PERCENT", "10"))
PAYMENT_TERMS_DAYS = int(os.environ.get("MILIMO_PAYMENT_TERMS_DAYS", "14"))
CURRENCY = os.environ.get("MILIMO_CURRENCY", "USD")
COMPLEXITY_TO_HOURS = {
    "low": int(os.environ.get("MILIMO_HOURS_LOW", "8")),
    "medium": int(os.environ.get("MILIMO_HOURS_MEDIUM", "20")),
    "high": int(os.environ.get("MILIMO_HOURS_HIGH", "40")),
    "complex": int(os.environ.get("MILIMO_HOURS_COMPLEX", "80")),
}
