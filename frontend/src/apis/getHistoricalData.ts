export default async (
  end_time: string,
  symbol: string,
  limit = 1000,
  interval = "1m"
) => {
  const response = await fetch(
    `http://localhost:8000/api/historical/${symbol}?` +
      `end_time=${end_time}&limit=${limit}&interval=${interval}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch data");
  }

  return await response.json();
};
