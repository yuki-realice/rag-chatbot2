/**
 * セル参照の解析ユーティリティ
 * Excelのセル参照（例：A2, B10）から行番号を抽出する
 */

/**
 * セル参照文字列から行番号を抽出
 * @param cell セル参照文字列（例："A2", "B10", "AA100"）
 * @returns 行番号（1ベース）
 * @throws Error 不正なセル参照形式の場合
 */
export function parseRowFromCell(cell: string): number {
  if (!cell || typeof cell !== 'string') {
    throw new Error('セル参照が空または無効です');
  }

  // 前後の空白を除去し、大文字に変換
  const normalizedCell = cell.trim().toUpperCase();

  // セル参照のパターン（列文字 + 行番号）
  const match = normalizedCell.match(/^([A-Z]+)(\d+)$/);
  
  if (!match) {
    throw new Error(`不正なセル参照形式です: ${cell}`);
  }

  const [, columnLetters, rowString] = match;
  
  // 行番号を数値に変換
  const rowNumber = parseInt(rowString, 10);
  
  if (isNaN(rowNumber) || rowNumber < 1) {
    throw new Error(`行番号は1以上である必要があります: ${rowString}`);
  }

  return rowNumber;
}

/**
 * セル参照文字列から列番号を抽出（A=1, B=2, ...）
 * @param cell セル参照文字列（例："A2", "B10", "AA100"）
 * @returns 列番号（1ベース）
 * @throws Error 不正なセル参照形式の場合
 */
export function parseColumnFromCell(cell: string): number {
  if (!cell || typeof cell !== 'string') {
    throw new Error('セル参照が空または無効です');
  }

  const normalizedCell = cell.trim().toUpperCase();
  const match = normalizedCell.match(/^([A-Z]+)(\d+)$/);
  
  if (!match) {
    throw new Error(`不正なセル参照形式です: ${cell}`);
  }

  const [, columnLetters] = match;
  
  // 列文字から列番号を計算（A=1, B=2, ..., Z=26, AA=27, etc.）
  let columnNumber = 0;
  for (let i = 0; i < columnLetters.length; i++) {
    const charCode = columnLetters.charCodeAt(i) - 'A'.charCodeAt(0) + 1;
    columnNumber = columnNumber * 26 + charCode;
  }
  
  return columnNumber;
}

/**
 * 行番号と列番号からセル参照文字列を生成
 * @param row 行番号（1ベース）
 * @param column 列番号（1ベース）
 * @returns セル参照文字列（例："A2", "B10"）
 */
export function createCellReference(row: number, column: number): string {
  if (row < 1 || column < 1) {
    throw new Error('行番号と列番号は1以上である必要があります');
  }

  // 列番号を文字に変換
  let columnLetters = '';
  let tempColumn = column;
  
  while (tempColumn > 0) {
    tempColumn--; // 0ベースに調整
    columnLetters = String.fromCharCode('A'.charCodeAt(0) + (tempColumn % 26)) + columnLetters;
    tempColumn = Math.floor(tempColumn / 26);
  }
  
  return `${columnLetters}${row}`;
}

/**
 * セル参照の妥当性をチェック
 * @param cell セル参照文字列
 * @returns 妥当な場合はtrue
 */
export function isValidCellReference(cell: string): boolean {
  try {
    parseRowFromCell(cell);
    parseColumnFromCell(cell);
    return true;
  } catch {
    return false;
  }
}

/**
 * セル参照の型定義
 */
export interface CellReference {
  row: number;
  column: number;
  cellAddress: string;
}

/**
 * セル参照文字列を構造化されたオブジェクトに変換
 * @param cell セル参照文字列
 * @returns CellReferenceオブジェクト
 */
export function parseCellReference(cell: string): CellReference {
  const row = parseRowFromCell(cell);
  const column = parseColumnFromCell(cell);
  
  return {
    row,
    column,
    cellAddress: cell.trim().toUpperCase()
  };
}
