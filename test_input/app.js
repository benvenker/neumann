/**
 * Sample JavaScript file for testing code-to-HTML rendering.
 * @module app
 */

/**
 * User class representing a user account
 */
class User {
  constructor(name, email) {
    this.name = name;
    this.email = email;
    this.createdAt = new Date();
  }

  /**
   * Get a formatted display name
   * @returns {string} The formatted name
   */
  getDisplayName() {
    return `${this.name} <${this.email}>`;
  }
}

/**
 * Fetch user data from an API
 * @param {number} userId - The user ID to fetch
 * @returns {Promise<User>} Promise resolving to user data
 */
async function fetchUser(userId) {
  const response = await fetch(`https://api.example.com/users/${userId}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return new User(data.name, data.email);
}

/**
 * Main application entry point
 */
async function main() {
  try {
    const user = await fetchUser(123);
    console.log(`Loaded user: ${user.getDisplayName()}`);
  } catch (error) {
    console.error('Failed to load user:', error);
  }
}

// Run the app
main();
