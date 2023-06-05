import Axios from "axios";
import * as k from "./k";
import type { ClientInterface } from "./types";
import { fileImageFills, fileImages, getFileNodes } from "./q";

export const Client = (): ClientInterface => {
  const clients = {
    file: Axios.create({
      baseURL: k.BUCKET_FIGMA_COMMUNITY_FILES_OFFICIAL_ARCHIVE,
    }),
    image: Axios.create({
      baseURL: k.BUCKET_FIGMA_COMMUNITY_IMAGES_OFFICIAL_ARCHIVE,
    }),
  };

  return {
    meta: (fileId) => clients.file.get(`/${fileId}/meta.json`),
    file: (fileId, params = {}) =>
      // params not supported atm
      clients.file.get(`/${fileId}/file.json.gz`),

    fileNodes: async (fileId, params) => {
      const res = await clients.file.get(`/${fileId}/file.json.gz`);
      const data = getFileNodes(res.data, params);
      return {
        ...res,
        data,
      };
    },

    fileImages: async (fileId, params) => {
      const res = await clients.image.get(`/${fileId}/exports/meta.json`);
      const { data } = res;

      return {
        ...res,
        data: fileImages(
          fileId,
          data,
          params,
          k.BUCKET_FIGMA_COMMUNITY_IMAGES_OFFICIAL_ARCHIVE
        ),
      };
    },

    fileImageFills: async (fileId) => {
      const res = await clients.image.get(`/${fileId}/images/meta.json`);
      const { data } = res;

      if (res.status === 200) {
        return {
          ...res,
          data: fileImageFills(
            fileId,
            data,
            k.BUCKET_FIGMA_COMMUNITY_IMAGES_OFFICIAL_ARCHIVE
          ),
        };
      } else {
        return res;
      }
    },
  };
};
