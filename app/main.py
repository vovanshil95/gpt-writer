import uuid
import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker
from  sqlalchemy.exc import IntegrityError
import openai

from models.models import Match, PromptBlank, FilledPrompt, GptInteraction, FavoritePrompt, FavoritePromptBlank, Workspace
from config import sqlalchemy_url, OPENAI_API_KEY, ORIGINS
from utils import BaseResponse
from workspace.router import router as workspace_router

class MatchSchema(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    color: str

class MatchResponse(BaseResponse):
    data: list[MatchSchema]

class PromptBlanksSchema(BaseModel):
    prompt: list[str]

class PromptsResponse(BaseResponse):
    data: PromptBlanksSchema

class GptAnswerSchema(BaseModel):
    gpt_response: str

class GptAnswerResponse(BaseResponse):
    data: GptAnswerSchema

class FavoritePromptSchema(BaseModel):
    id: uuid.UUID
    title: str
    prompt: list[str]

class FavoritePromptTimeSchema(FavoritePromptSchema):
    date_added: datetime.datetime

class FavoritePromptsTimeResponse(BaseResponse):
    data: list[FavoritePromptTimeSchema]

class FavoritePromptResponse(BaseResponse):
    data: FavoritePromptSchema

class FavoritePromptTimeResponse(BaseResponse):
    data: FavoritePromptTimeSchema

class GptRequestSchema(BaseModel):
    prompt: list[str]
    username: str
    company: str

class InteractionSchema(BaseModel):
    id: uuid.UUID
    request: GptRequestSchema
    datetime: datetime.datetime
    favorite: bool
    gpt_response: str

class InteractionsResponse(BaseResponse):
    data: list[InteractionSchema]

app = FastAPI()

sqlalchemy_session = sessionmaker(create_engine(sqlalchemy_url))
openai.api_key = OPENAI_API_KEY

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(workspace_router)

REQUEST_VALIDATION_ERROR_STATUS = 422
ENTITY_ERROR_STATUS = 400

def get_interactions(message: str) -> InteractionsResponse:
    with sqlalchemy_session.begin() as session:
        history = session.query(GptInteraction, func.array_agg(FilledPrompt.text_data)) \
            .filter(GptInteraction.workspace_id == session.query(Workspace.id).filter(Workspace.initial).first()[0]) \
            .join(FilledPrompt).group_by(GptInteraction.id)\
            .order_by(desc(GptInteraction.time_happened))\
            .all()
        history = list(map(lambda el: InteractionSchema(
            id=el[0].id,
            request=GptRequestSchema(
                prompt=el[1],
                username=el[0].username,
                company=el[0].company,
            ),
            datetime=el[0].time_happened,
            favorite=el[0].favorite,
            gpt_response=el[0].gpt_answer), history))
    return InteractionsResponse(status='success', message=message, data=history)

def get_favorite_prompts_(message: str) -> FavoritePromptsTimeResponse:
    with sqlalchemy_session.begin() as session:
        favorite_prompts = session.query(FavoritePrompt, func.array_agg(FavoritePromptBlank.text_data))\
            .filter(FavoritePrompt.workspace_id == session.query(Workspace.id).filter(Workspace.initial).first()[0]) \
            .join(FavoritePromptBlank).group_by(FavoritePrompt.id).order_by(desc(FavoritePrompt.date_added)).all()
        favorite_prompts = list(map(lambda p: FavoritePromptTimeSchema(id=p[0].id,
                                                                  title=p[0].title,
                                                                  date_added=p[0].date_added,
                                                                  prompt=p[1]), favorite_prompts))
    return FavoritePromptsTimeResponse(status='success', message=message, data=favorite_prompts)

@app.exception_handler(RequestValidationError)
def validation_handler(request, exc):
    return JSONResponse(status_code=ENTITY_ERROR_STATUS,
                        content={'status': 'error', 'message': exc.errors()[0]['msg']})


@app.exception_handler(IntegrityError)
def unique_vailation_handler(request, exc):
    if 'errors.UniqueViolation' in str(exc):
        return JSONResponse(status_code=ENTITY_ERROR_STATUS,
                            content={'status': 'error', 'message': 'Duplicate unique property detected'})
    else:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.exception_handler(AttributeError)
def entity_error_handler(request, exc):
    return JSONResponse(status_code=ENTITY_ERROR_STATUS, content={'status': 'error', 'message': str(exc)})


@app.get('/api/questions')
def get_questions() -> MatchResponse:
    with sqlalchemy_session.begin() as session:
        matches = session.query(Match)\
            .filter(Match.workspace_id == session.query(Workspace.id).filter(Workspace.initial).first()[0])\
            .all()
        matches = list(map(lambda m: MatchSchema(id=str(m.id),
                                                 question=m.question,
                                                 answer=m.answer,
                                                 color=m.color), matches))
    return MatchResponse(status='success', message='Questions successfully retrieved', data=matches)

@app.put('/api/questions')
def put_questions(questions: list[MatchSchema]) -> MatchResponse:
    with sqlalchemy_session.begin() as session:
        workspace_id = session.query(Workspace.id).filter(Workspace.initial).first()[0]
        session.query(Match)\
            .filter(Match.workspace_id == workspace_id)\
            .delete()
        session.add_all(map(lambda m: Match(m.id, m.question, m.answer, m.color, workspace_id), questions))
    return MatchResponse(status='success', message='Questions successfully saved', data=questions)

@app.get('/api/prompt')
def get_prompt() -> PromptsResponse:
    with sqlalchemy_session.begin() as session:
        prompts = session.query(PromptBlank) \
            .filter(PromptBlank.workspace_id == session.query(Workspace.id).filter(Workspace.initial).first()[0]) \
            .all()
        prompts = PromptBlanksSchema(prompt=list(map(lambda q: q.text_data, prompts)))
    return PromptsResponse(status='success', message='Prompt successfully retrieved', data=prompts)

@app.put('/api/prompt')
def put_prompt(prompts: PromptBlanksSchema) -> PromptsResponse:
    with sqlalchemy_session.begin() as session:
        workspace_id = session.query(Workspace.id).filter(Workspace.initial).first()[0]
        session.query(PromptBlank).filter(PromptBlank.workspace_id == workspace_id).delete()
        session.add_all(list(map(lambda pr: PromptBlank(uuid.UUID(hex=str(uuid.uuid4())), pr, workspace_id), prompts.prompt)))
    return PromptsResponse(status='success', message='Prompt successfully saved', data=prompts)

@app.get('/api/history')
def get_history() -> InteractionsResponse:
    return get_interactions('History successfully retrieved')


@app.put('/api/response')
def get_response(request: GptRequestSchema) -> GptAnswerResponse:
    response = openai.ChatCompletion.create(model='gpt-4', messages=[{'role': 'user', 'content': '\n'.join(request.prompt)}])
    answer = response['choices'][0]['message']['content']
    interaction_id = uuid.UUID(hex=str(uuid.uuid4()))
    with sqlalchemy_session.begin() as session:
        session.add(GptInteraction(interaction_id, answer, request.username,
                                   request.company,
                                   datetime.datetime.now(ZoneInfo('Europe/Moscow')),
                                   session.query(Workspace.id).filter(Workspace.initial).first()[0]))
        session.flush()
        session.add_all(map(lambda pr: FilledPrompt(uuid.UUID(hex=str(uuid.uuid4())), pr, interaction_id), request.prompt))
    return GptAnswerResponse(status='success', message='GPT Response successfully retrieved', data={'gpt_response': answer})


@app.get('/api/favoritePrompts')
def get_favorite_prompts() -> FavoritePromptsTimeResponse:
    return get_favorite_prompts_('Favorite prompts successfully retrieved')

@app.put('/api/favoritePrompts')
def put_favorite_prompts(prompt: FavoritePromptSchema) -> FavoritePromptTimeResponse:
    with sqlalchemy_session.begin() as session:
        date_added = datetime.datetime.now(ZoneInfo('Europe/Moscow'))
        session.add(FavoritePrompt(id=prompt.id,
                                   title=prompt.title,
                                   date_added=date_added,
                                   workspace_id=session.query(Workspace.id).filter(Workspace.initial).first()[0]))
        session.flush()
        session.add_all(list(map(lambda p: FavoritePromptBlank(uuid.UUID(hex=str(uuid.uuid4())), prompt.id, p), prompt.prompt)))
        favorite_prompt = FavoritePromptTimeSchema(id=prompt.id, title=prompt.title, prompt=prompt.prompt, date_added=date_added)
    return FavoritePromptTimeResponse(status='success', message='Favorite prompt successfully saved', data=favorite_prompt)

@app.delete('/api/favoritePrompts')
def delete_favorite_prompts(id: uuid.UUID) -> FavoritePromptsTimeResponse:
    with sqlalchemy_session.begin() as session:
        prompt = session.get(FavoritePrompt, id)
        if not prompt: raise AttributeError("Id doesn't exist")
        session.delete(prompt)
    return get_favorite_prompts_('Favorite prompt successfully deleted')

@app.put('/api/favoriteHistory')
def add_to_favorite(id: uuid.UUID)->InteractionsResponse:
    with sqlalchemy_session.begin() as session:
        session.get(GptInteraction, id).favorite = True
    return get_interactions('Interaction successfully added to favorite')

@app.delete('/api/favoriteHistory')
def delete_from_favorite(id: uuid.UUID)->InteractionsResponse:
    with sqlalchemy_session.begin() as session:
        session.get(GptInteraction, id).favorite = False
    return get_interactions('Interaction successfully deleted from favorite')