#!/usr/bin/env python3
"""Sample Python file for testing code-to-HTML rendering."""


def greet(name: str, enthusiastic: bool = False) -> str:
    """Generate a greeting message.

    Args:
        name: The name to greet
        enthusiastic: Whether to add extra emphasis

    Returns:
        A greeting string
    """
    greeting = f"Hello, {name}!"
    if enthusiastic:
        greeting += " Nice to meet you!"
    return greeting


class Person:
    """Represents a person with a name and age."""

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def introduce(self) -> str:
        """Return an introduction string."""
        return f"I'm {self.name} and I'm {self.age} years old."


def main():
    """Main entry point."""
    people = [
        Person("Alice", 30),
        Person("Bob", 25),
        Person("Charlie", 35),
    ]

    for person in people:
        print(greet(person.name, enthusiastic=True))
        print(person.introduce())
        print()


if __name__ == "__main__":
    main()
