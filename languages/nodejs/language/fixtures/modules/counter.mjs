export let count = 0;

export default count;

export function increment() {
  count += 1;
  return count;
}

export function reset() {
  count = 0;
}
