import { useState } from "react";
import { InstructorContentApi } from "../../services/instructorContentApi";

export default function ContentEditor({
  moduleId,
  onSaved,
}) {
  const [materialTitle, setMaterialTitle] =
    useState("");

  const [materialBody, setMaterialBody] =
    useState("");

  const [mediaTitle, setMediaTitle] =
    useState("");

  const [mediaUrl, setMediaUrl] =
    useState("");

  const [mediaType, setMediaType] =
    useState("video");

  async function createReadingMaterial() {
    await InstructorContentApi.createMaterial(
      moduleId,
      {
        title: materialTitle,
        body: materialBody,
        order_index: 0,
      }
    );

    setMaterialTitle("");
    setMaterialBody("");

    onSaved?.();
  }

  async function createMediaContent() {
    await InstructorContentApi.createMedia(
      moduleId,
      {
        title: mediaTitle,
        media_url: mediaUrl,
        media_type: mediaType,
        order_index: 0,
      }
    );

    setMediaTitle("");
    setMediaUrl("");

    onSaved?.();
  }

  return (
    <div>

      <h4>Add Reading Material</h4>

      <input
        className="form-control mb-2"
        placeholder="Title"
        value={materialTitle}
        onChange={(e) =>
          setMaterialTitle(e.target.value)
        }
      />

      <textarea
        className="form-control mb-2"
        rows="6"
        placeholder="Content"
        value={materialBody}
        onChange={(e) =>
          setMaterialBody(e.target.value)
        }
      />

      <button
        className="btn btn-primary mb-4"
        onClick={createReadingMaterial}
      >
        Create Material
      </button>

      <hr />

      <h4>Add Media Content</h4>

      <input
        className="form-control mb-2"
        placeholder="Title"
        value={mediaTitle}
        onChange={(e) =>
          setMediaTitle(e.target.value)
        }
      />

      <input
        className="form-control mb-2"
        placeholder="Media URL"
        value={mediaUrl}
        onChange={(e) =>
          setMediaUrl(e.target.value)
        }
      />

      <select
        className="form-select mb-2"
        value={mediaType}
        onChange={(e) =>
          setMediaType(e.target.value)
        }
      >
        <option value="video">Video</option>
        <option value="image">Image</option>
        <option value="audio">Audio</option>
        <option value="document">Document</option>
      </select>

      <button
        className="btn btn-success"
        onClick={createMediaContent}
      >
        Create Media
      </button>

    </div>
  );
}