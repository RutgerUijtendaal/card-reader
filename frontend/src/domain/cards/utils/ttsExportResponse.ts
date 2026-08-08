export type TtsExportResponse = {
  encodedPayload: string;
  exportedCount: number;
  skippedCount: number;
  sheetCount: number;
};

export type TtsExportApiResponse = {
  encoded_payload: string;
  exported_count: number;
  skipped_count: number;
  sheet_count: number;
};

export const mapTtsExportResponse = (response: TtsExportApiResponse): TtsExportResponse => ({
  encodedPayload: response.encoded_payload,
  exportedCount: response.exported_count,
  skippedCount: response.skipped_count,
  sheetCount: response.sheet_count,
});

export const ttsExportSheetDescription = (result: TtsExportResponse): string => {
  const descriptions = [
    `Uses ${result.sheetCount} persistent sheet${result.sheetCount === 1 ? '' : 's'}.`,
  ];
  if (result.skippedCount > 0) {
    descriptions.push(
      `${result.skippedCount} card${result.skippedCount === 1 ? '' : 's'} could not be exported.`,
    );
  }
  return descriptions.join(' ');
};
