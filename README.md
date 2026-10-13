# lz — 류신 지퍼 결합 파트너 탐색 및 설계

두 개의 α-나선을 각각 다른 단백질에 붙여 단백질끼리 연결하는 시스템을 만들려면,
먼저 **표적 나선에 강하게, 그리고 선택적으로 붙는 파트너**가 필요합니다.
이 패키지는 그 파트너를 서열 수준에서 찾고 설계합니다.

## 핵심 설계 원칙

**결합력만 보면 안 됩니다.** 파트너가 표적에 아무리 세게 붙어도 자기들끼리
호모다이머를 만들어 버리면 용액 속에서 표적과 만나지 못합니다. 그래서 이 도구는
모든 후보를 **특이성(specificity)** — 이종이량체가 경쟁하는 호모다이머를 얼마나
이기는가 — 로 순위를 매깁니다. 결합 점수가 아니라.

## 설치

```bash
pip install pytest numpy
```

핵심 기능은 표준 라이브러리만 씁니다. numpy는 `calibrate`에만, pytest는 테스트에만 필요합니다.

## 실행 프로그램 (GUI)

**Python 없이 실행**하려면 `dist\lz.exe` — 단일 파일이고 설치가 필요 없습니다.

소스에서 실행하려면 `run-gui.bat` 더블클릭, 또는:

```bash
python -m lz gui
```

### exe 다시 빌드하기

```bash
build-exe.bat
```

아이콘 생성 → PyInstaller 빌드 → **자체 점검**까지 세 단계입니다. 마지막 단계가
중요합니다: 창만 뜨는 exe는 데이터 파일이 빠져도 멀쩡히 시작했다가 사용자가
버튼을 눌러야 터집니다. 자체 점검은 그 경로들을 헤드리스로 실행하고 보고서를
씁니다.

```bash
dist\lz.exe --selftest report.txt
```

```
frozen: True
_MEIPASS: C:\...\Temp\_MEI000066a42
library path: C:\...\Temp\_MEI000066a42\data\zippers.json
PASS  library file exists: True
PASS  library loads: 5 zippers
PASS  screening: 5 hits
PASS  orthogonal design: RMEQMESRIKAIRKRMKAMEGQMSSLQRRIAKV
OK
```

빌드 실패 시 `build-exe.bat`이 0이 아닌 코드로 끝나므로 깨진 exe를 배포할 수 없습니다.

알아둘 점:
- **첫 실행이 2~5초 걸립니다.** 단일 파일 빌드는 매번 임시 폴더에 압축을 풉니다.
  빠른 시작이 필요하면 `lz.spec`에서 `COLLECT`를 쓰는 폴더 형태로 바꾸세요.
- **백신이 오탐할 수 있습니다.** PyInstaller 단일 파일 exe의 알려진 문제이고,
  서명되지 않은 빌드라 더 그렇습니다. 사내 배포라면 코드 서명을 권합니다.
- `numpy`는 번들에서 제외했습니다 (GUI가 쓰지 않음). 그래서 `lz calibrate`는
  exe가 아니라 소스에서 돌려야 합니다.

Tkinter 기반이라 **설치할 것이 없고, 서버도 네트워크도 쓰지 않습니다** —
미공개 구조를 다룰 때 중요한 점입니다.

화면은 위에서 아래로 네 단계입니다:

1. **target structure** — `Open PDB...`로 구조 파일을 열거나, 서열을 직접 입력
2. **measured geometry** — 사슬 목록, 측정된 헵타드 레지스터, 평행/역평행,
   결합된 리간드. 역평행이거나 레지스터가 애매하면 **빨간 경고**가 뜹니다
3. **find partners** — 세 가지 분석
   - `Screen known zippers` — 라이브러리 순위
   - `Design partners` — 이 표적 전용 파트너 설계
   - `Design orthogonal set` — 표적을 고정한 채 직교 쌍 세트 설계
4. **ranked candidates** — 점수 표. 열 제목을 클릭하면 정렬되고,
   초록색 행은 표적을 자기 호모다이머보다 선호하는 후보입니다

`Save CSV...`로 표를 내보내고, `Save AlphaFold FASTA...`로 C단계 입력을
만듭니다 (이종이량체와 호모다이머를 함께 써서 특이성을 비교할 수 있게 합니다).

무거운 계산은 작업 스레드에서 돌아가므로 창이 멈추지 않고, 진행률이 표시됩니다.

## 직교 세트 설계

파트너 하나로는 보통 부족합니다. 단백질 연결 시스템을 실제로 쓰려면
**서로 간섭하지 않는 쌍이 여러 개** 필요합니다 — A는 A′를, B는 B′를 찾되
A가 B′에 붙으면 안 됩니다.

```bash
python -m lz orthogonal --pdb my_zipper.pdb --pairs 2 --seed 5
```

직교성은 어느 한 쌍의 성질이 아니므로 **쌍을 하나씩 설계해서는 얻을 수 없습니다.**
K쌍이면 2K개 나선에 K(2K−1)가지 상호작용이 가능한데 그중 원하는 건 K개뿐이고,
나머지 전부가 경쟁 상태입니다. 그래서 전체 집합을 상호작용 행렬 전체에 대해
동시에 최적화합니다.

```
           A       A'        B       B'
A     -14.3    -19.1*   -15.6    -14.0
A'    -19.1*   -13.6    -14.4    -16.2
B     -15.6    -14.4    -16.3    -18.7*
B'    -14.0    -16.2    -18.7*   -17.1

* = 의도한 쌍. 나머지 모든 칸이 이겨야 할 off-target
```

**설계 마진(`--margin`, 기본 3.0)이 결정적입니다.** 측정 결과:

| 마진 | 공동 설계 | 독립 설계 |
|---|---|---|
| 1.0 | −1.20 | **−1.89** |
| 2.0 | −1.98 | −2.07 |
| 3.0 | **−2.72** | −1.81 |
| 4.0 | **−3.11** | −1.41 |

마진 1.0에서는 공동 설계가 **오히려 더 나빴습니다.** cognate 점수가 −20 근처라
경쟁자를 1만큼 이기는 건 아무것도 아니고, hinge가 즉시 꺼져서 탐색이 쌍들을
차별화하기도 전에 멈춥니다. 공동 설계는 바가 충분히 높아서 실제로 coiled coil을
가르는 수단(*a*의 묻힌 극성 잔기, e/g의 반대 전하 패턴)을 쓰도록 강제될 때만
값을 합니다. 자세한 건 `orthogonal.py`의 `DEFAULT_CROSS_MARGIN` 주석에.

## 시험용 구조

```bash
python tools/fetch_structure.py 2ZTA
```

`structures/2ZTA.pdb` — GCN4 류신 지퍼(O'Shea et al. 1991), 이 분야의 표준
참조 구조입니다. `tests/test_real_structure.py`가 이걸로 회귀 테스트를 돌리고,
파일이 없으면 자동으로 건너뜁니다(오프라인에서도 스위트가 돌아감).

구조는 커밋하지 않습니다 — 남의 데이터이고, RCSB가 정본입니다.

## PDB 파일로 시작하기

구조가 있으면 헵타드 레지스터를 **예측하지 않고 측정**합니다. 서열만 쓸 때
가장 불확실한 단계가 사라지므로, 가능하면 이쪽을 쓰세요.

```bash
python -m lz pdb my_zipper.pdb          # 구조 확인
python -m lz screen --pdb my_zipper.pdb # 라이브러리 순위
python -m lz design --pdb my_zipper.pdb --seed 1
```

`lz pdb` 출력 예시:

```
chain A vs chain B
  orientation   parallel
  heptad offset 6 (first residue at 'g')
  register fit  0.849 (margin 0.274)

  measured core residues (cosine 1.0 = pointing straight at partner):
    a  MET2       +0.88
    d  LEU5       +0.89
    a  ASN16      +0.79
    ...
```

cosine은 각 잔기의 곁사슬이 상대 나선을 얼마나 똑바로 향하는지입니다
(1.0 = 정면). 이 값으로 7가지 오프셋을 채점해 레지스터를 정합니다.

구조가 **역평행**이면 경고가 뜹니다. 점수 모델은 평행 이중나선만 가정하므로
그 경우 순위는 의미가 없습니다. 사슬이 하나뿐이면 상대가 없어 측정이 불가능하고,
서열 예측으로 자동 폴백하면서 그 사실을 알려줍니다.

## 사용법 (서열로 시작할 때)

### 1. 헵타드 레지스터 확인

```bash
python -m lz register RMKQLEDKVEELLSKNYHLENEVARLKKLVGER
```

```
    1  RMKQLEDKVEELLSKNYHLENEVARLKKLVGER
       gabcdefgabcdefgabcdefgabcdefgabcd

offset      6 (first residue sits at 'g')
confidence  1.260 (clear)
core (a/d)  MLVLNLVLVR
```

`confidence`가 0.5 미만이면 레지스터가 애매하다는 뜻입니다. `--offset`으로 직접 지정하세요.

### 2. 알려진 지퍼 라이브러리 스크리닝

```bash
python -m lz screen <표적서열>
```

`spec` 열이 음수여야 쓸 만한 후보입니다. 양수면 그 후보는 표적보다 자기 자신을 더 좋아합니다.

### 3. 새 파트너 설계

```bash
python -m lz design <표적서열> --seed 1 --top 5 --fasta designs.fasta
```

위치별 허용 아미노산(*a*: ILVNAM, *d*: LMAIV, *e*/*g*: EKQR …)을 제한한 상태에서
모의 담금질로 탐색합니다. 목적함수는:

```
objective = E(이종이량체)
          + w_self   · max(0, E(이종) + margin − E(파트너 호모다이머))
          + w_target · max(0, E(이종) + margin − E(표적 호모다이머))
```

뒤의 두 항이 음성 설계입니다. **hinge 형태인 것이 중요합니다** — 선형으로 두면
설계기가 자기 호모다이머를 망가뜨리는 것만으로 점수를 무한정 낮출 수 있어서,
정작 이종이량체 계면을 포기해 버립니다 (개발 중 실제로 코어 Leu를 전부 Ile로
바꿔버렸습니다). 자세한 내용은 `params.py`의 `SPECIFICITY_MARGIN` 주석에.

### 4. 구조 예측으로 넘기기 (C 단계)

```bash
python -m lz export <표적서열> --seed 1 --top 5 --out complexes.fasta
```

ColabFold / AlphaFold-Multimer용 FASTA를 씁니다. 이종이량체뿐 아니라 **호모다이머도
같이** 내보냅니다 — 둘을 비교해야 특이성을 확인할 수 있기 때문입니다.
판정 기준은 명령 출력에 함께 나옵니다.

### 5. 저분자 도킹 준비 — 읽고 쓰세요

```bash
python -m lz dockprep my_zipper.pdb --out-dir docking
```

계면을 찾아 박스를 씌우고, 깨끗한 receptor PDB와 AutoDock Vina 설정 파일을 씁니다.
**도킹을 실행하지도, 저분자에 점수를 매기지도 않습니다.** `lz`에는 저분자
점수 함수가 없습니다 — 그건 Vina/Smina/Glide 같은 엔진과 화합물 라이브러리가
있어야 하는 일입니다.

그리고 더 중요한 이야기: **류신 지퍼 계면은 저분자에게 최악에 가까운 표적입니다.**
닫힌 포켓이 없는, 길고 얕고 용매에 노출된 소수성 띠 — 교과서적인 "undruggable"
단백질-단백질 계면입니다. 이런 표면에서는 도킹 점수가 "기름진 표면을 얼마나 많이
덮느냐"에 지배되어, 크고 소수성 높은 분자를 무조건 높게 치고 실제 결합과는 잘
맞지 않습니다. 위양성이 많이 나올 것을 각오하세요.

`dockprep`은 이 판단을 구조에서 직접 계산해 알려줍니다:

```
hydrophobic core    80%
  - The interface is strongly hydrophobic (80% of core residues). Docking will
    favour large greasy compounds that are unlikely to be selective or soluble.
  - The groove is 46 A long and shallow rather than pocket-like. No single
    small molecule covers that much interface; a peptide does.
```

**단백질을 연결하는 것이 목적이라면 저분자가 아니라 설계된 파트너 나선이 맞는
도구입니다** (`lz design`). 저분자 도킹은 지퍼를 *사용*하려는 게 아니라
*방해*하려 할 때만 의미가 있습니다.

### 6. 실험 데이터로 보정

```bash
python -m lz calibrate my_tm_data.csv --out weights.json
python -m lz screen <표적서열> --weights weights.json
```

CSV 열: `sequence1,sequence2,tm`. 최소제곱으로 세 항의 가중치를 맞추고 R²/RMSE를 보고합니다.

## 점수의 한계 — 꼭 읽으세요

점수는 **순위용이지 에너지가 아닙니다.** `params.py`의 상수는 두 종류입니다:

- **측정값**: 나선 성향은 Pace & Scholtz (1998)에서 그대로 가져왔습니다.
- **휴리스틱**: 코어 패킹과 염다리 값은 확립된 *정성적* 규칙(*d*의 Leu 선호,
  Harbury의 Ile/Leu 올리고머 규칙, GCN4 Asn16의 이량체 특이성, 묻힌 전하의 불안정화)을
  손으로 인코딩한 것입니다. **어떤 데이터셋에도 피팅되지 않았습니다.**

그래서 `predicted_tm`은 보정 전에는 의미가 없습니다. 숫자를 인용하려면 먼저
`calibrate`를 돌리세요.

또한 이 모델은 **평행 이중나선 coiled coil만** 다룹니다. 역평행 배향, 삼량체/사량체,
나선 밖 영역의 기여는 보지 않습니다. 그것들이 C 단계가 필요한 이유입니다.

## 서열 라이브러리의 출처

`data/zippers.json`의 모든 항목에는 `recall` 필드가 있습니다. 이건 지퍼가 얼마나
좋은지가 아니라 **그 서열 문자열을 얼마나 믿어도 되는지**를 나타냅니다. 어떤 항목도
데이터베이스에서 자동으로 가져온 것이 아니라 기억에서 적힌 것이므로,
**실험 전에 반드시 원 논문과 대조하십시오.**

직교 세트를 늘리려면 다음을 직접 추가하는 것을 권합니다:
SYNZIP1–23 (Thompson et al. 2012, ACS Synth Biol 1:118), Woolfson lab CC-Di/CC-Tri,
Keating lab bZIP array. JSON이나 FASTA로 `--library`에 넘기면 됩니다.

## 구조

```
dist/lz.exe                빌드된 단일 실행파일
build-exe.bat              아이콘 -> 빌드 -> 자체 점검
run-gui.bat / lz-gui.pyw   소스에서 실행
lz.spec                    PyInstaller 설정
tools/make_icon.py         아이콘 생성
lz/
  gui.py        Tkinter 데스크톱 앱
  orthogonal.py 직교 세트 공동 설계
  structure.py  PDB 파싱, 나선 검출, 기하학적 레지스터 측정
  heptad.py     서열 기반 헵타드 레지스터 예측
  params.py     파라미터 테이블 (출처 표기 포함)
  scoring.py    코어 패킹 + g↔e' 정전기 + 나선 성향
  design.py     음성 설계 포함 모의 담금질
  library.py    라이브러리 로딩 및 스크리닝
  export.py     AlphaFold-Multimer 핸드오프 (C 단계)
  dockprep.py   저분자 도킹 입력 준비 (도킹은 하지 않음)
  cli.py        명령줄 인터페이스
data/zippers.json
tests/
  make_structure.py   Crick 식으로 정답을 아는 구조 생성
  test_lz.py          서열 수준 기능
  test_structure.py   구조 파싱 및 레지스터 측정
  test_orthogonal.py  직교 세트 설계
  test_gui.py         GUI 배선 및 워커 스레드
  test_dockprep.py    도킹 준비 및 CLI
```

## 테스트

```bash
python -m pytest tests -q
```

테스트는 절대 에너지를 검증하지 않습니다 (보정 전 상수를 검증하는 꼴이므로).
대신 역학(레지스터가 제자리에 가는가, 점수가 올바른 섭동에 반응하는가)과
정성적 생물물리 기대(Leu가 *d*에서 최적인가, 묻힌 동일 전하가 벌점을 받는가)를 봅니다.

구조 테스트는 PDB 엔트리를 받아 쓰지 않습니다 — 그러면 "논문을 내가 제대로 읽었나"를
검증하는 순환 논증이 됩니다. 대신 `tests/make_structure.py`가 Crick 매개변수식으로
좌표를 생성하는데, 여기서는 **레지스터가 입력값**입니다. 정답이 측정 코드와
독립적으로 나오므로 측정의 정확도를 진짜로 검증할 수 있습니다.
