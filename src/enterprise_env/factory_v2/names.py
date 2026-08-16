"""Deterministic name pools for factory_v2 entity generation.

All lists are static so the RNG position, not the list, drives variation.
"""
from __future__ import annotations

FIRST_NAMES = [
    "Alex", "Jordan", "Riley", "Morgan", "Casey", "Taylor", "Dana", "Quinn",
    "Jamie", "Avery", "Rohan", "Priya", "Arjun", "Maya", "Sarah", "Daniel",
    "Emma", "James", "Olivia", "Noah", "Aisha", "Wei", "Yuki", "Carlos", "Elena",
    "Lena", "Marco", "Nina", "Omar", "Pham", "Rafi", "Sona", "Tara", "Uma", "Vera",
    "Kai", "Lee", "Sam", "Chris", "Pat", "Drew", "Sage", "River", "Sky", "Ash",
]

LAST_NAMES = [
    "Chen", "Patel", "Kim", "Johnson", "Martinez", "Singh", "Williams", "Brown",
    "Davis", "Miller", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White",
    "Harris", "Thompson", "Rao", "Kumar", "Zhang", "Nakamura", "Rodriguez", "Lewis",
    "Scott", "Evans", "Hall", "Walker", "Allen", "Young", "Hernandez", "King", "Wright",
    "Lopez", "Hill", "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter", "Mitchell",
    "Perez", "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Collins", "Edwards",
]

VENDOR_ADJECTIVES = [
    "Quantum", "Stellar", "Cyber", "Data", "Cloud", "Smart", "Swift", "Core",
    "Link", "Net", "Prime", "Apex", "Nexus", "Atlas", "Summit", "Vertex",
    "Zenith", "Pioneer", "Orbit", "Flux", "Pulse", "Grid", "Wave", "Arc",
    "Nova", "Helix", "Prism", "Synapse", "Vector", "Cascade", "Echo", "Forge",
]

VENDOR_NOUNS = [
    "Systems", "Analytics", "Solutions", "Dynamics", "Logic", "Works",
    "Bridge", "Sync", "Base", "Forge", "Labs", "Technologies", "Platforms",
    "Ventures", "Networks", "Intelligence", "Services", "Engines", "Metrics",
    "Group", "Partners", "Collective", "Associates", "Innovations", "Research",
]
