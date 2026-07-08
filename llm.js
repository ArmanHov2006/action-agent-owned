export async function ask(messages) {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages,
      tools: [
        {
          type: 'function',
          function: {
            name: 'httpGet',
            description: 'Fetch contents of a URL over HTTP GET.',
            parameters: {
              type: 'object',
              properties: { url: { type: 'string' } },
              required: ['url'],
            },
          },
        },
        {
          type: 'function',
          function: {
            name: 'finish',
            description: 'Call this once the task is fully complete.',
            parameters: {
              type: 'object',
              properties: { summary: { type: 'string' } },
              required: ['summary'],
            },
          },
        },
      ],
    }),
  })
  const data = await response.json()
  console.log(JSON.stringify(data))
  return data.choices[0].message
}
