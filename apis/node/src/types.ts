import { AxiosPromise } from "axios";
import * as Figma from "@design-sdk/figma-remote-types";

export interface FileParams {
  /**
   * A list of nodes that you care about in the document.
   * If specified, only a subset of the document will be returned corresponding to the nodes listed, their children, and everything between the root node and the listed nodes
   */
  readonly ids?: ReadonlyArray<string>;

  /**
   * Positive integer representing how deep into the document tree to traverse.
   * For example, setting this to 1 returns only Pages, setting it to 2 returns Pages and all top level objects on each page.
   * Not setting this parameter returns all nodes
   *
   * if using typescript, for number bigger than typed number, use `n as any` - e.g. `100 as any`
   *
   * @allowed `>= 1` (`0` will throw an error)
   */
  readonly depth?: 1 | 2 | 3 | 4 | 5 | 6 | 8 | 9 | 10; // any number greater than 0 is acceptable

  /**
   * Set to "paths" to export vector data
   */
  readonly geometry?: "paths";
}

export interface FileNodesParams {
  /** A list of node IDs to retrieve and convert */
  readonly ids: ReadonlyArray<string>;

  /**
   * Positive integer representing how deep into the document tree to traverse. For example, setting this to 1 returns only Pages, setting it to 2 returns Pages and all top level objects on each page. Not setting this parameter returns all nodes
   */
  readonly depth?: number;

  /**
   * Set to "paths" to export vector data
   */
  readonly geometry?: string;
}

export type exportFormatOptions = "jpg" | "png" | "svg" | "pdf";

export interface FileImageParams {
  /** A list of node IDs to render */
  readonly ids: ReadonlyArray<string>;
  /** A number between 0.01 and 4, the image scaling factor */
  readonly scale?: number;
  /** A string enum for the image output format, can be "jpg", "png", "svg", or "pdf" */
  readonly format?: exportFormatOptions;
}

export interface ClientInterface {
  readonly meta: (fileId: string) => AxiosPromise<any>;

  /**
   * Returns the document refered to by :key as a JSON object.
   * The file key can be parsed from any Figma file url:
   * https://www.figma.com/file/:key/:title.
   * The "document" attribute contains a Node of type DOCUMENT.
   * @param {fileId} String File to export JSON from
   * @see https://www.figma.com/developers/api#get-files-endpoint
   */
  readonly file: (
    fileId: string,
    params?: FileParams
  ) => AxiosPromise<Figma.FileResponse>;

  // /**
  //  * Returns the nodes referenced to by :ids as a JSON object.
  //  * The nodes are retrieved from the Figma file referenced to by :key.
  //  * The node Id and file key can be parsed from any Figma node url:
  //  * https://www.figma.com/file/:key/:title?node-id=:id.
  //  * @param {fileId} String File to export JSON from
  //  * @param {params} FileNodesParams
  //  * @see https://www.figma.com/developers/api#get-file-nodes-endpoint
  //  */
  // readonly fileNodes: (
  //   fileId: string,
  //   params: FileNodesParams
  // ) => AxiosPromise<Figma.FileNodesResponse>;

  /**
   * If no error occurs, "images" will be populated with a map from
   * node IDs to URLs of the rendered images, and "status" will be omitted.
   * Important: the image map may contain values that are null.
   * This indicates that rendering of that specific node has failed.
   * This may be due to the node id not existing, or other reasons such
   * has the node having no renderable components. It is guaranteed that
   * any node that was requested for rendering will be represented in this
   * map whether or not the render succeeded.
   * @param {fileId} String File to export images from
   * @param {params} FileImageParams
   * @see https://www.figma.com/developers/api#get-images-endpoint
   */
  readonly fileImages: (
    fileId: string,
    params: FileImageParams
  ) => AxiosPromise<Figma.FileImageResponse>;

  /**
   * Returns download links for all images present in image fills in a document.
   * Image fills are how Figma represents any user supplied images.
   * When you drag an image into Figma, we create a rectangle with a single
   * fill that represents the image, and the user is able to transform the
   * rectangle (and properties on the fill) as they wish.
   *
   * This endpoint returns a mapping from image references to the URLs at which
   * the images may be download. Image URLs will expire after no more than 14 days.
   * Image references are located in the output of the GET files endpoint under the
   * imageRef attribute in a Paint.
   * @param {fileId} String File to export images from
   * @see https://www.figma.com/developers/api#get-image-fills-endpoint
   */
  readonly fileImageFills: (
    fileId: string
  ) => AxiosPromise<Figma.FileImageFillsResponse>;
}
