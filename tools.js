export async function httpGet(url) {
  const response = await fetch(url)
  const data = await response.text()
  return data
}
