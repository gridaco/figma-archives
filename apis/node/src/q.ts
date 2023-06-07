import type {
  FileImageResponse,
  FileImageFillsResponse,
  FileResponse,
  FileNodesResponse,
  Node,
  Document,
} from "@design-sdk/figma-remote-types";
import type { FileImageParams, FileNodesParams } from "./types";

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
      images: Object.keys(meta.images).reduce((acc, key) => {
        const image = meta.images[key];
        return {
          ...acc,
          [key]: `${baseURL}/${fileId}/images/${image}`,
        };
      }, {}),
    },
  };
}

/**
 * get node by id from a document recursively
 * @param document file.document object
 * @param id
 * @returns
 */
export function getNodeById(document: Document, id: string) {
  const _ = (node: Node, id: string): Node | undefined => {
    if (node.id === id) {
      return node;
    }
    if ("children" in node) {
      for (const child of node.children) {
        const match = _(child, id);
        if (match) {
          return match;
        }
      }
    }
  };

  const node = _(document, id);

  return node;
}

export function getFileNodes(
  file: FileResponse,
  params: FileNodesParams
): FileNodesResponse {
  const { ids, depth: __no__depth, geometry: __no__geometry } = params;
  // 1. geometry is not used. the archived data is pulled with geometry already.
  // setting geometry to "paths" will not change the result in destruptive way, it only adds more data to the result anyway.
  // 2. depth is not used. the archived data is pulled with full depth already, no need to optimize with depth.

  const {
    document,
    components,
    styles,
    lastModified,
    name,
    thumbnailUrl,
    version,
  } = file;

  const nodes = ids
    // 1. map the nodes
    .map((id) => getNodeById(document, id))
    // reduce as to match the response type
    .reduce((prev, curr) => {
      if (curr) {
        prev[curr.id] = <FileNodesResponse["nodes"][string]>{
          // TODO:
          // 2. map the components
          components: {},
          // TODO:
          // 3. map the styles
          styles: {},
          document: curr,
        };
      }
      return prev;
    }, {} as Mutable<FileNodesResponse["nodes"]>);

  return {
    lastModified: lastModified,
    name: name,
    role: "viewer",
    thumbnailUrl: thumbnailUrl,
    version: version,
    nodes: nodes,
  };
}

type Mutable<T> = {
  -readonly [P in keyof T]: T[P];
};
