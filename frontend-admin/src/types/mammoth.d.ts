// mammoth는 타입 정의를 제공하지 않아, 실제로 쓰는 API만 최소로 선언한다.
declare module "mammoth" {
  export function extractRawText(input: { arrayBuffer: ArrayBuffer }): Promise<{
    value: string
    messages: unknown[]
  }>
}
