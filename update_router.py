import re

router_file = 'src/contexts/document_intake_ocr/presentation/api/routers/batch_router.py'
with open(router_file, 'r', encoding='utf-8') as f:
    router_content = f.read()

import_statement = "from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import get_reprocess_dossier_use_case\nfrom src.contexts.document_intake_ocr.application.use_cases.reprocess_dossier_use_case import ReprocessDossierUseCase\n"
if "get_reprocess_dossier_use_case" not in router_content:
    router_content = router_content.replace(
        "from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import (",
        import_statement + "from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import ("
    )

route_func = '''
@router.post(
    "/{batch_id}/dossiers/{dni_reference}/reprocess",
    status_code=status.HTTP_200_OK,
    summary="Reprocesa todo el expediente (todos sus documentos) con IA",
)
async def reprocess_entire_dossier(
    batch_id: UUID,
    dni_reference: str,
    background_tasks: BackgroundTasks,
    current_user: TokenClaims = Depends(get_current_user),
    use_case: ReprocessDossierUseCase = Depends(get_reprocess_dossier_use_case),
):
    return await use_case.execute(
        batch_id=batch_id,
        dni_reference=dni_reference,
        user_email=current_user.email,
        background_tasks=background_tasks,
    )
'''
if "reprocess_entire_dossier" not in router_content:
    router_content += route_func

with open(router_file, 'w', encoding='utf-8') as f:
    f.write(router_content)
