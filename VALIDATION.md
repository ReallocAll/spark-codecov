# 实际验证记录

验证日期：2026-09-11。以下运行属于当前 `ReallocAll/spark-codecov` 仓库；此前已删除的误建仓库运行不作为验收证据。最终构建的基础设施提交为 [`1cde2f3aff06afbf11e773e071c8f6f70269510d`](https://github.com/ReallocAll/spark-codecov/commit/1cde2f3aff06afbf11e773e071c8f6f70269510d)。

## 最终结果

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

四种模式均在第 89 行获得完整指针证据。第 87 行反汇编及重定位表确认 O0 重新读取已被 hook 的 getpid GOT 槽，O1/O2 则使用先前保存在寄存器中的原始地址；不带覆盖率的 O0 同样失败。正式模式据此采用 Debug＋O1，保持所有插桩及源断言；未扩展 gateway 豁免。诊断仅运行普通 ELF 测试，未单独证明 preload 测试或完整 CTest 通过，也不属于覆盖率验收。临时诊断工作流和脚本已移除，提交历史与运行 artifact 保留证据。正式模式的完整 CTest、报告与上传仍需新运行验证。
