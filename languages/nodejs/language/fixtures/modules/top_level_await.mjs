const events = ['module start'];
await Promise.resolve();
events.push('module resumed');

export { events };
export const ready = true;
