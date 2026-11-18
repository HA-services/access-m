# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
"""Tiny helpers for domains in prefix notation, so the module does not depend on
odoo.osv.expression, which is not available in every supported version."""

_OPERATORS = ('&', '|', '!')


def normalize_domain(domain):
    """Return the domain with every implicit AND written out."""
    result = []
    expected = 1
    for token in domain:
        if expected == 0:
            result.insert(0, '&')
            expected = 1
        if isinstance(token, (list, tuple)):
            expected -= 1
        elif token != '!':
            expected += 1
        result.append(token)
    return result


def AND(domains):
    """Combine domains with a logical AND, ignoring empty ones."""
    parts = [normalize_domain(list(d)) for d in domains if d]
    if not parts:
        return []
    result = []
    for part in parts:
        result.extend(part)
    return ['&'] * (len(parts) - 1) + result
