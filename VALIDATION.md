# 实际验证记录

## 最新验收：2026-09-12

测试的基础设施提交为 [`f25933608465e9008f378b8d7715803303123439`](https://github.com/ReallocAll/spark-codecov/commit/f25933608465e9008f378b8d7715803303123439)。所有源文件与断言保持不变；Debug 消费者、RelWithDebInfo 依赖及全部 CTest 保留。

| 源提交 | 完整 CTest | gcovr XML 行覆盖 | XML 文件数 | 实现编译命令：插桩 / 豁免 |
| --- | --- | --- | --- | --- |
| 历史 SHA `61bbec4043c87f149ad84841951b36a2125c000b` | **137/137** | 18,609 / 23,140，**80.42%** | 177 | 169 / 5 |
| develop → `1c0e54981fab6735bee714394012ba905f817b97` | **168/168** | 19,284 / 23,793，**81.05%** | 181 | 192 / 0 |

- 历史：[运行 34668026548](https://github.com/ReallocAll/spark-codecov/actions/runs/34668026548)，[artifact 10290460531](https://github.com/ReallocAll/spark-codecov/actions/runs/34668026548/artifacts/10290460531)；上传按 `false` 跳过。
- 当前：[运行 34668028651](https://github.com/ReallocAll/spark-codecov/actions/runs/34668028651)，[artifact 10290146291](https://github.com/ReallocAll/spark-codecov/actions/runs/34668028651/artifacts/10290146291)；构建、报告及上传成功。

两次完整套件均包含通过的 Python、ELF-domain 与 preload 测试，没有跳过测试。有效 `-O1`、严格 XML 校验均通过；两次 Actions 中固定 SHA 的源检出执行 `git diff --exit-code HEAD` 均返回 0，此结论不涉及本地 Spark 工作区状态。历史与当前分别有 179 / 183 个 HTML 页面，本地资源缺失数均为 0。当前仅豁免 parser fixture 的两个测试编译命令，192 个 `src/` 实现编译命令全部插桩；历史版本的五项豁免均符合精确 gateway 合约。

两次均使用已验证的 Python 3.12.14 共享库 `/opt/hostedtoolcache/Python/3.12.14/x64/lib/libpython3.12.so.1.0`。修复包括精确的无启动回调目标豁免、按源 CI 配置 `SPARK_TEST_LIBPYTHON`、使用 `--merge-mode-functions=separate` 保留函数位置差异并继续合并源码行，以及有指针与反汇编证据支持的 Debug＋O1。未添加错误忽略选项或源码范围排除。

**当前上传已确认处理与归属：** [Codecov 提交 API](https://api.codecov.io/api/v2/github/ReallocAll/repos/spark/commits/1c0e54981fab6735bee714394012ba905f817b97/)返回正确 SHA、`develop` 与 `complete`；[上传 API](https://api.codecov.io/api/v2/github/ReallocAll/repos/spark/commits/1c0e54981fab6735bee714394012ba905f817b97/uploads/)的 `merged` 记录明确指向本次运行 `34668028651`。上传 UUID 为 `69f51e77-674e-475f-80ea-9968765458b4`，创建于 2026-09-12 02:54:46 UTC，合并于 02:54:52 UTC。服务指标 **55.61%** 与 XML **81.05%** 分别记录；175 个服务端文件及全部服务端行均属于 XML 的 `src/` 集合，没有增加路径或行。

### 本次修复的运行证据

| 运行 | 观察结果 |
| --- | --- |
| [34646975899](https://github.com/ReallocAll/spark-codecov/actions/runs/34646975899) | 原始失败：带 `-nostartfiles` 的 gateway 链接覆盖率运行时时缺少 `__dso_handle`，测试尚未开始。 |
| [34664903016](https://github.com/ReallocAll/spark-codecov/actions/runs/34664903016) | gateway 链接已修复；历史版本 132/137 测试通过，剩余为三项 Python 运行时配置缺失及两项 ELF 断言；另有 gcovr 函数位置合并冲突。 |
| [34664904810](https://github.com/ReallocAll/spark-codecov/actions/runs/34664904810) | 当前版本 163/168 测试通过，失败类别相同；精确豁免与全部实现插桩审计通过。 |
| [34666958708](https://github.com/ReallocAll/spark-codecov/actions/runs/34666958708) | 四模式诊断确认 O0/O1 地址加载差异，详见本文末尾；不是覆盖率验收。 |
| [34664893850](https://github.com/ReallocAll/spark-codecov/actions/runs/34664893850)、[34665920907](https://github.com/ReallocAll/spark-codecov/actions/runs/34665920907)、[34668016014](https://github.com/ReallocAll/spark-codecov/actions/runs/34668016014) | 对应修复的基础设施检查通过，最终为 27 项测试。 |

组织上传仍未验证，缺少 `CODECOV_TOKEN_ENDSTONE`；这不影响上述个人仓库修复与实际上传验收。最新验证不新增 Windows、BDS 或玩家交互覆盖率声明。

## 历史验收：2026-09-11

以下运行属于当前 `ReallocAll/spark-codecov` 仓库；此前已删除的误建仓库运行不作为验收证据。当时测试的基础设施提交为 [`1cde2f3aff06afbf11e773e071c8f6f70269510d`](https://github.com/ReallocAll/spark-codecov/commit/1cde2f3aff06afbf11e773e071c8f6f70269510d)。

| 源仓库与 ref | 源 SHA | CTest | gcovr XML 行覆盖 | XML 文件数 |
| --- | --- | --- | --- | --- |
| `ReallocAll/spark` · `develop` | [`12371158ed2ccc8cc81ea15b62ea9bbd911414d5`](https://github.com/ReallocAll/spark/commit/12371158ed2ccc8cc81ea15b62ea9bbd911414d5) | 72/72，通过 | 14,276 / 19,410，73.55% | 166，含 86 个 `.cpp` |
| `EndstoneMC/spark` · `main` | [`8958173ad40c1da9adf3254305526443c9853848`](https://github.com/EndstoneMC/spark/commit/8958173ad40c1da9adf3254305526443c9853848) | 29/29，通过 | 8,811 / 12,506，70.45% | 107，含 51 个 `.cpp` |

- 个人：[运行 34561379385](https://github.com/ReallocAll/spark-codecov/actions/runs/34561379385)，[下载 artifact 10184622678](https://github.com/ReallocAll/spark-codecov/actions/runs/34561379385/artifacts/10184622678)，2,868,024 字节；构建、报告校验与上传步骤成功。
- 组织：[运行 34561381754](https://github.com/ReallocAll/spark-codecov/actions/runs/34561381754)，[下载 artifact 10184594394](https://github.com/ReallocAll/spark-codecov/actions/runs/34561381754/artifacts/10184594394)，1,885,047 字节；构建与报告校验成功，按 `upload_to_codecov=false` 跳过上传。

Artifact 保留 14 天，下载可能需要 GitHub 登录。也可执行：

```sh
gh run download 34561379385 --repo ReallocAll/spark-codecov --dir reports/personal
gh run download 34561381754 --repo ReallocAll/spark-codecov --dir reports/endstone
```

两次运行均通过实际 gcda 存在性检查、编译命令覆盖率检查、严格 XML 路径与计数校验，源仓库 `git diff --exit-code HEAD` 返回 0。个人 168 个、组织 109 个 HTML 页面完成本地链接和资源文件检查，缺失数均为 0。Metadata 中的源 SHA、基础设施 SHA、`ref_type=branch`、分支归属和运行 URL 均符合预期。

实际工具版本：Ubuntu 24.04，Clang/LLVM 20.1.8，Python 3.12.14，CMake 3.31.10，Conan 2.32.0，gcovr 8.6，Ninja 1.13.2。消费者为 Debug，依赖保留 profile 的 RelWithDebInfo；profile 未修改。覆盖范围仅为该 Linux 离线构建中的 `src/` 实现和实例化头文件，含手写 proto；不代表 Windows、真实 BDS 或玩家交互覆盖率。

## Codecov 请求、处理与归属

个人运行上传请求明确指定 `ReallocAll/spark`、源 SHA `12371158ed2ccc8cc81ea15b62ea9bbd911414d5`、分支 `develop`。Action 成功仅是请求证据；以下公开服务端记录进一步确认本次上传：

- [提交 API](https://api.codecov.io/api/v2/github/ReallocAll/repos/spark/commits/12371158ed2ccc8cc81ea15b62ea9bbd911414d5/)：上传前返回 404，上传后对应 SHA 状态为 `complete`。
- [上传 API](https://api.codecov.io/api/v2/github/ReallocAll/repos/spark/commits/12371158ed2ccc8cc81ea15b62ea9bbd911414d5/uploads/)：状态 `merged`，`build_url` 指向本次运行 `34561379385`。
- 上传存储 UUID：`aa7dc147-01b5-4a16-93ab-5e0da3de7621`；创建于 2026-09-11 04:22:50 UTC，合并完成于 04:23:00 UTC。
- [Codecov 提交页面](https://app.codecov.io/github/reallocall/spark/commit/12371158ed2ccc8cc81ea15b62ea9bbd911414d5) 服务指标为 **49.49%**；本地 gcovr XML 行覆盖率为 **73.55%**，两者计算口径不同。

将[服务端报告](https://api.codecov.io/api/v2/github/ReallocAll/repos/spark/report/?sha=12371158ed2ccc8cc81ea15b62ea9bbd911414d5)与实际 XML 逐文件、逐行对照：服务端 159 个文件及全部行均属于 XML 的 166 个文件与行集合，路径全部位于 `src/`，未增加测试、第三方或未编译文件。服务端移除了 2,541 个 XML 行记录，其中 1,793 行有命中、748 行零命中；剩余有命中的行中，4,133 行因分支覆盖不完整计为 partial。于是 Codecov 的完整命中行数为 `14,276 − 1,793 − 4,133 = 8,350`，总行数为 `19,410 − 2,541 = 16,869`，覆盖率为 `8,350 / (8,350 + 4,386 + 4,133) = 49.49%`；gcovr 则为 `14,276 / 19,410 = 73.55%`。[Codecov FAQ](https://docs.codecov.com/docs/frequently-asked-questions)说明 partial 不计入覆盖率分子，[报告修正规则](https://docs.codecov.com/docs/fixing-reports)说明默认 C/C++ 大括号修正；本次未逐行证明所有被移除记录的具体修正原因。

范围由实际编译记录决定，不按文件名排除平台：例如 `statistics_profile_windows.cpp` 在本次 Linux 构建中有测量数据，因此保留；未编译的 Windows 实现不因此进入报告。

组织上传尚未验证：当前缺少 `CODECOV_TOKEN_ENDSTONE`。最小后续操作是在本基础设施仓库配置该组织源仓库 token，然后执行 README 中的组织上传命令：

```sh
gh workflow run coverage.yml --repo ReallocAll/spark-codecov --ref main -f source_repository=EndstoneMC/spark -f source_ref=main -F upload_to_codecov=true
```

## 其他实际运行

| 运行 | 观察结果 |
| --- | --- |
| [34560261148](https://github.com/ReallocAll/spark-codecov/actions/runs/34560261148) | 初始基础设施检查成功，15 项单元测试通过。 |
| [34561368339](https://github.com/ReallocAll/spark-codecov/actions/runs/34561368339) | 行合并修复后的基础设施检查成功。 |
| [34560270417](https://github.com/ReallocAll/spark-codecov/actions/runs/34560270417) | 个人 72/72 测试通过；初始 gcovr XML 同一行存在函数实例重复记录，被校验器拒绝，未上传。 |
| [34560273611](https://github.com/ReallocAll/spark-codecov/actions/runs/34560273611) | 组织 29/29 测试通过；同样因重复行记录被拒绝，未上传。修复为报告命令添加 `--merge-lines`，未改源测试。 |
| [34560304740](https://github.com/ReallocAll/spark-codecov/actions/runs/34560304740) | 不存在的源 ref 在 prepare 阶段失败，构建跳过。 |
| [34560307301](https://github.com/ReallocAll/spark-codecov/actions/runs/34560307301) | 组织 `main` 上传缺少所选 token，在 prepare 阶段失败，构建跳过。 |
| [34560339625](https://github.com/ReallocAll/spark-codecov/actions/runs/34560339625) | 完整 SHA 成功解析，随后因缺少组织 token 在 prepare 阶段失败，构建跳过。 |

标签与完整 SHA 的解析已单独验证；未验证标签上传。本文与 README 的后续文档提交不改变已测试实现，且不匹配工作流的代码路径触发条件，不会因此启动完整构建。


## 2026-09-12 ELF 编译模式诊断

[诊断运行 34666958708](https://github.com/ReallocAll/spark-codecov/actions/runs/34666958708)固定源提交 `1c0e54981fab6735bee714394012ba905f817b97`，基础设施提交 `e673437148f00cc166d8d550d8706107b59a059f`；[artifact 10289458572](https://github.com/ReallocAll/spark-codecov/actions/runs/34666958708/artifacts/10289458572)保存普通 CTest、编译命令、GDB 指针和反汇编记录。

| 模式 | 普通 ELF 测试 | 第 89 行的候选指针 |
| --- | --- | --- |
| 带覆盖率 `-O0` | 失败，CTest 退出码 8 | `Imported == replacement != original` |
| 不带覆盖率 `-O0` | 失败，CTest 退出码 8 | `Imported == replacement != original` |
| 带覆盖率 `-O1` | 通过，CTest 退出码 0 | `Imported == original != replacement` |
| 带覆盖率 `-O2` | 通过，CTest 退出码 0 | `Imported == original != replacement` |

四种模式均在第 89 行获得完整指针证据。第 87 行反汇编及重定位表确认 O0 重新读取已被 hook 的 getpid GOT 槽，O1/O2 则使用先前保存在寄存器中的原始地址；不带覆盖率的 O0 同样失败。正式模式据此采用 Debug＋O1，保持所有插桩及源断言；未扩展 gateway 豁免。诊断仅运行普通 ELF 测试，未单独证明 preload 测试或完整 CTest 通过，也不属于覆盖率验收。临时诊断工作流和脚本已移除，提交历史与运行 artifact 保留证据。随后正式模式的完整 CTest、报告与当前源提交上传均已通过本文开头的 2026-09-12 两次运行验证。
