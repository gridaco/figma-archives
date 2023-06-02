import type { FileImageResponse } from "@design-sdk/figma-remote-types";
import type { FileImageParams } from "./types";
import { FileImageFillsResponse } from "@design-sdk/figma-remote-types";

export function fileImages(
  fileId: string,
  meta: any,
  { format: _format, ids, scale: _scale }: FileImageParams,
  baseURL: string
): FileImageResponse {
  const format = _format || "png";
  const scale = _scale || 1;

  const images = ids.reduce((acc, id) => {
    const exports: Array<string> = meta.map[id];
    const resolution = exports.find(
      (d: string) => d === `@${scale}x.${format}`
    );
    const url =
      scale === 1 || scale === undefined
        ? `${baseURL}/${fileId}/exports/${id}.${format}`
        : `${baseURL}/${fileId}/exports/${id}${resolution}`;
    return {
      ...acc,
      [id]: url,
    };
  }, {});

  return {
    err: null,
    images,
  };
}

export function fileImageFills(
  fileId: string,
  meta: any,
  baseURL: string
): FileImageFillsResponse {
  return {
    error: false,
    status: 200,
    meta: {
      images: Object.keys(meta.meta.images).reduce((acc, key) => {
        const image = meta.meta.images[key];
        return {
          ...acc,
          [key]: `${baseURL}/${fileId}/images/${image}`,
        };
      }, {}),
    },
  };
}
