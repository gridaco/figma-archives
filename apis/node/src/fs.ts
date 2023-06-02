import fs from "fs/promises";
import path from "path";
import mime from "mime-types";
import type { AxiosResponse, AxiosRequestHeaders } from "axios";
import type { ClientInterface } from "./types";
import { fileImageFills, fileImages } from "./fmt";

const _mock_axios_request = async <T = any>(
  path: string
): Promise<AxiosResponse<T>> => {
  try {
    const { size: content_length } = await fs.stat(path);
    const content_type = mime.lookup(path) || "application/json";
    return {
      data: JSON.parse(await fs.readFile(path, "utf-8")) as T,
      status: 200,
      statusText: "OK",
      headers: {},
      config: {
        headers: {
          Accept: content_type,
          "Content-Length": content_length,
          "User-Agent": "@figma-api/community/fs",
          "Content-Encoding": "utf-8",
          "Content-Type": "application/json",
        } as AxiosRequestHeaders,
      },
    };
  } catch (e) {
    return {
      data: null as any,
      status: 404,
      statusText: "Not Found",
      headers: {},
      config: {
        headers: {} as AxiosRequestHeaders,
      },
    };
  }
};

export const Client = ({
  paths,
}: {
  paths: {
    file: string;
    image: string;
  };
}): ClientInterface => {
  const clients = {
    file: {
      get: async (url: string) =>
        _mock_axios_request(path.join(paths.file, url)),
    },
    image: {
      get: async (url: string) =>
        _mock_axios_request(path.join(paths.image, url)),
    },
  };

  return {
    meta: (fileId) => clients.file.get(`/${fileId}/meta.json`),
    file: (fileId, params = {}) =>
      // params not supported atm
      clients.file.get(`/${fileId}/file.json`),

    // fileNodes: (fileId, params) =>
    //   clients.file.get(`files/${fileId}/nodes`, {
    //     params: {
    //       ...params,
    //       ids: params.ids.join(","),
    //     },
    //   }),

    fileImages: async (fileId, params) => {
      const res = await clients.image.get(`/${fileId}/exports/meta.json`);
      const { data } = res;

      return {
        ...res,
        data: fileImages(fileId, data, params, paths.image),
      };
    },

    fileImageFills: async (fileId) => {
      const res = await clients.image.get(`/${fileId}/images/meta.json`);
      const { data } = res;

      if (res.status === 200) {
        return {
          ...res,
          data: fileImageFills(fileId, data, paths.image),
        };
      } else {
        return res;
      }
    },
  };
};
