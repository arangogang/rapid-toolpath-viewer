MODULE MoveAbsJTest
  CONST jointtarget jHome := [[0,0,0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p10 := [[500,0,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];

  PROC main()
    MoveAbsJ jHome, v1000, z50, tool0;
    MoveL p10, v100, fine, tool0;
  ENDPROC
ENDMODULE
