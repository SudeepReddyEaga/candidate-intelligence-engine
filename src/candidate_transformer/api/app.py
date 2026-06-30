from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import ValidationError as PydanticValidationError

from candidate_transformer.domain import ProjectionConfig, SourcePayload, SourceType, TransformInput
from candidate_transformer.pipeline import CandidateTransformer
from candidate_transformer.utils.errors import CandidateTransformerError
from candidate_transformer.utils.logging import configure_logging


async def _payload(upload: UploadFile | None, source_type: SourceType) -> SourcePayload | None:
    if upload is None:
        return None
    content = await upload.read()
    print(f"DEBUG: _payload {source_type} filename='{upload.filename}' len={len(content)}")
    if not content or not content.strip():
        return None
    return SourcePayload(
        source_type=source_type,
        name=upload.filename or source_type.value,
        content=content,
    )


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Candidate Intelligence Engine",
        version="0.1.0",
        description="Multi-source candidate data transformer with confidence and provenance.",
    )
    transformer = CandidateTransformer()

    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import RedirectResponse
    import os

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="static")

    @app.get("/")
    def root():
        return RedirectResponse(url="/ui/index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/transform")
    async def transform(
        resume: Annotated[UploadFile | None, File(description="Resume PDF")] = None,
        csv_file: Annotated[
            UploadFile | None, File(alias="csv", description="Recruiter CSV")
        ] = None,
        ats_json: Annotated[UploadFile | None, File(description="ATS JSON")] = None,
        github_json: Annotated[UploadFile | None, File(description="GitHub profile JSON")] = None,
        notes: Annotated[UploadFile | None, File(description="Recruiter notes")] = None,
        config: Annotated[str | None, Form(description="Projection config JSON string")] = None,
    ) -> dict[str, Any]:
        try:
            sources = [
                source
                for source in [
                    await _payload(resume, SourceType.RESUME_PDF),
                    await _payload(csv_file, SourceType.CSV),
                    await _payload(ats_json, SourceType.ATS_JSON),
                    await _payload(github_json, SourceType.GITHUB_JSON),
                    await _payload(notes, SourceType.NOTES),
                ]
                if source is not None
            ]
            if not sources:
                raise CandidateTransformerError("At least one source file is required")
            projection = ProjectionConfig()
            if config and config != "string":
                projection = ProjectionConfig.model_validate(json.loads(config))
            result = transformer.transform(TransformInput(sources=sources, projection=projection))
            try:
                with open("transform_output.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                import logging
                logging.getLogger("uvicorn.error").error(f"Failed to save output to transform_output.json: {e}")
            return result
        except (
            CandidateTransformerError,
            PydanticValidationError,
            json.JSONDecodeError,
            KeyError,
        ) as exc:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
