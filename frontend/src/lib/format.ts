export const label = (value: string) =>
  value.replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase());
export const time = (value: string) =>
  new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
