module.exports = {
  // ...
  plugins: ['unused-imports'],
  rules: {
    // warn or error, your choice:
    'unused-imports/no-unused-imports': 'error',
    // optionally remove unused vars if prefixed with _
    'unused-imports/no-unused-vars': [
      'warn',
      { vars: 'all', varsIgnorePattern: '^_', args: 'after-used', argsIgnorePattern: '^_' }
    ]
  }
}
