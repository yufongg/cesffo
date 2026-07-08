// Loaded automatically by react-scripts before each test file.
// Adds jest-dom matchers such as toBeInTheDocument().
import '@testing-library/jest-dom';

// Jest's jsdom environment does not provide TextEncoder/TextDecoder,
// which react-router v7 requires at import time.
import { TextEncoder, TextDecoder } from 'util';

if (typeof global.TextEncoder === 'undefined') {
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}
