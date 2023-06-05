import Axios from "axios";
import * as k from "./k";
import type { ClientInterface } from "./types";
import { fileImageFills, fileImages } from "./fmt";

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
      // {
      //   params: {
      //     ...params,
      //     ids: params.ids ? params.ids.join(",") : "",
      //   },
      // }
      clients.file.get(`/${fileId}/file.json.gz`),

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
